from jinja2 import Environment, FileSystemLoader
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import datetime
import kopf
import yaml
import json
import os, time
import re
import random
import asyncio

def getRecordName(name):
  return f'dns-operator-{name}'.replace('.','-')

def genDNSDeployment(name,namespace,zonelist,replicas):
  file_path = os.path.dirname(os.path.realpath(__file__)) + "/templates"
  environment = Environment(loader=FileSystemLoader(file_path))
  template = environment.get_template("deployment.j2")
  body = template.render(name=name.replace('.','-'),namespace=namespace,zonelist=zonelist,replicas=replicas)
  return(yaml.safe_load(body))    

def genDNSConfigmap(name,namespace,zonelist):
  file_path = os.path.dirname(os.path.realpath(__file__)) + "/templates"
  environment = Environment(loader=FileSystemLoader(file_path))
  template = environment.get_template("configmap.j2")
  body = template.render(name=name.replace('.','-'),namespace=namespace,zonelist=zonelist)
  return(yaml.safe_load(body))

def genDNSTCPService(name,namespace,lbtype):
  file_path = os.path.dirname(os.path.realpath(__file__)) + "/templates"
  environment = Environment(loader=FileSystemLoader(file_path))
  template = environment.get_template("service-tcp.j2")
  body = template.render(name=name.replace('.','-'),namespace=namespace,lbtype=lbtype)
  return(yaml.safe_load(body))

def genDNSUDPService(name,namespace,lbtype):
  file_path = os.path.dirname(os.path.realpath(__file__)) + "/templates"
  environment = Environment(loader=FileSystemLoader(file_path))
  template = environment.get_template("service-udp.j2")
  body = template.render(name=name.replace('.','-'),namespace=namespace,lbtype=lbtype)
  return(yaml.safe_load(body))


async def rolloutDeployment (deployment,namespace,timeout,logger):
  now = datetime.datetime.utcnow()
  now = str(now.isoformat("T") + "Z")
  body = {
      'spec': {
          'template':{
              'metadata': {
                  'annotations': {
                      'kubectl.kubernetes.io/restartedAt': now
                  }
              }
          }
      }
  }
  try:
    v1_apps = client.AppsV1Api()
    start = time.time()
    v1_apps.patch_namespaced_deployment(deployment, namespace, body, pretty='true')
    while time.time() - start < timeout:
      #time.sleep(2)
      await asyncio.sleep(2.0)
      response = v1_apps.read_namespaced_deployment_status(deployment,namespace)
      s = response.status
      if (s.updated_replicas == response.spec.replicas and
              s.replicas == response.spec.replicas and
              s.available_replicas == response.spec.replicas and
              s.observed_generation >= response.metadata.generation):
          logger.info('Rollout deployment finish without errors')
          return True
      else:
          pass
          #logger.info(f'[updated_replicas:{s.updated_replicas},replicas:{s.replicas}, available_replicas:{s.available_replicas},observed_generation:{s.observed_generation}] waiting...')
    raise RuntimeError(f'Waiting timeout for deployment {deployment}')
  except ApiException as e:
      e=str(e).replace('\n','\\n')
      error_msg=f'{{"error": {e}}}'
      logger.error("Exception when calling rolloutDeployment: %s\n" % error_msg)

#https://kopf.readthedocs.io/en/stable/peering/?highlight=wait#multi-pod-operators
@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.peering.priority = random.randint(0, 32767) 
    settings.peering.stealth = True

@kopf.on.create('dnsservers')
async def create_dnsservers(spec, name, namespace, logger, **kwargs):
  deployment = genDNSDeployment(name,namespace,spec.get('zones'),spec.get('replicas'))
  configmap = genDNSConfigmap(name,namespace,spec.get('zones'))
  service_tcp = genDNSTCPService(name,namespace,'LoadBalancer')
  service_udp = genDNSUDPService(name,namespace,'LoadBalancer')
  try:
    v1_core = client.CoreV1Api()
    v1_apps = client.AppsV1Api()
    # Make unnecesary to manage deletion
    kopf.adopt(deployment)
    kopf.adopt(configmap)
    kopf.adopt(service_tcp)
    kopf.adopt(service_udp)
    v1_apps.create_namespaced_deployment(namespace,deployment,pretty='true')
    v1_core.create_namespaced_config_map(namespace,configmap,pretty='true')
    v1_core.create_namespaced_service(namespace,service_tcp,pretty='true')
    v1_core.create_namespaced_service(namespace,service_udp,pretty='true')
    await asyncio.sleep(1.0)
  except ApiException as e:
      e=str(e).replace('\n','\\n')
      error_msg=f'{{"error": {e}}}'
      logger.error("Exception when calling create_dnsServer: %s\n" % error_msg)
  return {'dsnserver-name': name}


@kopf.on.create('dnsrecords')
async def create_dnsrecords(spec, name, namespace, logger,bypass_rollout=False, **kwargs):
  try:
    # Get some contextual data
    zone=spec.get('zone')
    dnsServerRef=spec.get('dnsServerRef')
    recordType=spec.get('recordType')
    recordKey=spec.get('recordKey')
    recordValue=spec.get('recordValue')
    configMapName=f'dns-operator-{dnsServerRef}'.replace('.','-')
    zoneName=f'db.{zone}'
    v1_core = client.CoreV1Api()
    currentConfigMap = v1_core.read_namespaced_config_map(namespace=namespace,name=configMapName)
    currentZoneValue = currentConfigMap.data[zoneName]
    # Verify record doesn't exit
    # if not re.search(f'{recordKey} (.*) IN {recordType} (.*)',data):
    if currentZoneValue.find(f'{recordKey} IN {recordType}') > 0:
      logger.warning(f'Record "{recordKey} IN {recordType}" already exists, removing it before procesing')
      currentZoneValue=re.sub(f'{recordKey} IN {recordType} .*(?:\n|$)','',currentZoneValue)
    # Add it
    newZoneValue=currentZoneValue
    for item in recordValue:
      newZoneValue+=f'{recordKey} IN {recordType} {item}\n' 
      logger.info(f'Adding Record "{recordKey} IN {recordType} {item}')
    newZoneValue = newZoneValue.replace('\n','\\n')
    patch_body=yaml.safe_load(f'[{{ "op": "replace", "path": "/data/db.{zone}", "value": "{newZoneValue}"}}]')
    v1_core.patch_namespaced_config_map(configMapName,namespace,patch_body,pretty='true')
    if not bypass_rollout:
        await rolloutDeployment (f'dns-operator-{dnsServerRef}'.replace('.','-'),namespace,60,logger)
    now = datetime.datetime.utcnow()
    return json.dumps({'last_event': now},default=str)
  except ApiException as e:
    e=str(e).replace('\n','\\n')
    error_msg=f'{{"error": {e}}}'
    logger.error("Exception when calling create_dnsrecords: %s\n" % error_msg)

@kopf.on.update('dnsrecords')
async def update_dnsrecords(spec, old, new, name, namespace, logger, diff, **_):
  # Delete and create it
  await delete_dnsrecords(old.get('spec'),name,namespace,logger,bypass_rollout=True)
  await create_dnsrecords(new.get('spec'),name,namespace,logger)
  now = datetime.datetime.utcnow()
  return json.dumps({'last_event': now},default=str)

@kopf.on.delete('dnsrecords')
async def delete_dnsrecords(spec, name, namespace, logger,bypass_rollout=False, **kwargs):
  try:
    # Get some contextual data
    zone=spec.get('zone')
    dnsServerRef=spec.get('dnsServerRef')
    recordType=spec.get('recordType')
    recordKey=spec.get('recordKey')
    recordValue=spec.get('recordValue')
    configMapName=f'dns-operator-{dnsServerRef}'.replace('.','-')
    zoneName=f'db.{zone}'
    v1_core = client.CoreV1Api()
    currentConfigMap = v1_core.read_namespaced_config_map(namespace=namespace,name=configMapName)
    currentZoneValue = currentConfigMap.data[zoneName]
    # Verify record exit
    if currentZoneValue.find(f'{recordKey} IN {recordType}'):
      logger.info(f'Deleting record "{recordKey} IN {recordType}"')
      newZoneValue=re.sub(f'{recordKey} IN {recordType} .*(?:\n|$)','',currentZoneValue)
      newZoneValue = newZoneValue.replace('\n','\\n')
      patch_body=yaml.safe_load(f'[{{ "op": "replace", "path": "/data/db.{zone}", "value": "{newZoneValue}"}}]')
      v1_core.patch_namespaced_config_map(configMapName,namespace,patch_body,pretty='true')
      if not bypass_rollout:
        await rolloutDeployment (f'dns-operator-{dnsServerRef}'.replace('.','-'),namespace,60,logger)
    else:
      logger.warning(f'Record "{recordKey} IN {recordType}" does not exists, ignoring delete')
    now = datetime.datetime.utcnow()
    return json.dumps({'last_event': now},default=str)
  except ApiException as e:
    e=str(e).replace('\n','\\n')
    error_msg=f'{{"error": {e}}}'
    logger.error("Exception when calling replaceConfigMap: %s\n" % error_msg)

config.load_kube_config()  # for local environment
#config.load_incluster_config()  A
