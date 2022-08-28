from jinja2 import Environment, FileSystemLoader
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import datetime
import os, time

def genDNSDeployment(name,namespace,zonelist):
  file_path = os.path.dirname(os.path.realpath(__file__)) + "/templates"
  environment = Environment(loader=FileSystemLoader(file_path))
  template = environment.get_template("deployment.j2")
  body = template.render(name=name,namespace=namespace,zonelist=zonelist)
  return(body)    

def genDNSConfigmap (name,namespace,zonelist):
  file_path = os.path.dirname(os.path.realpath(__file__)) + "/templates"
  environment = Environment(loader=FileSystemLoader(file_path))
  template = environment.get_template("confirmap.j2")
  body = template.render(name=name,namespace=namespace,zonelist=zonelist)
  return(body)

def rolloutDeployment (deployment,namespace,timeout=60):
  # config.load_kube_config()  # for local environment
  # #config.load_incluster_config()
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
      time.sleep(2)
      response = v1_apps.read_namespaced_deployment_status(deployment,namespace)
      s = response.status
      if (s.updated_replicas == response.spec.replicas and
              s.replicas == response.spec.replicas and
              s.available_replicas == response.spec.replicas and
              s.observed_generation >= response.metadata.generation):
          return True
      else:
          print(f'[updated_replicas:{s.updated_replicas},replicas:{s.replicas}, available_replicas:{s.available_replicas},observed_generation:{s.observed_generation}] waiting...')
    raise RuntimeError(f'Waiting timeout for deployment {deployment}')
  except ApiException as e:
      print("Exception when calling AppsV1Api->read_namespaced_deployment_status: %s\n" % e)

def replaceConfigMap(name, namespace,zone):
  # config.load_kube_config()  # for local environment
  # #config.load_incluster_config()  A
  try:
    v1 = client.CoreV1Api()
    currentZoneValue = v1.read_namespaced_config_map(namespace=namespace,name=name).data[zone]
    #any('runner2  IN CNAME' in string for string in currentZoneValue)

  except ApiException as e:
    print("Exception when calling replaceConfigMap: %s\n" % e)

config.load_kube_config()  # for local environment
#config.load_incluster_config()  A

# deployment = genDNSDeployment("dnsinstance01","default",["example.org", "0.0.10.in-addr.arpa"])
# configmap = genDNSConfigmap("dnsinstance01","default",["example.org", "0.0.10.in-addr.arpa"])
# print(deployment+"\n---\n"+configmap)
rolloutDeployment ("dns-operator-dnsinstance01","default")
