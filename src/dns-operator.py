import kopf, logging, random
import asyncio
from kubernetes import client, config
from kubernetes.client.rest import ApiException

import filednsoperator as filednsoperator

def get_provider(namespace,dnsname):
  v1 = client.CustomObjectsApi()
  try:
    instance = v1.get_namespaced_custom_object(group="davidp1404.github.com", version="v1", plural="dnsservers",namespace=namespace,name=dnsname)
    return instance['spec']['provider']
  except ApiException as e:
    return ""

#https://kopf.readthedocs.io/en/stable/peering/?highlight=wait#multi-pod-operators
@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.peering.priority = random.randint(0, 32767) 
    settings.peering.stealth = True
    settings.peering.standalone = False
    settings.posting.level = logging.INFO

@kopf.on.create('dnsservers')
async def create_dnsservers(spec, name, namespace, logger, **kwargs):
  if spec.get('provider') == "corednsFiles":
    return(await filednsoperator.create_dnsservers(spec, name, namespace, logger, **kwargs))

@kopf.on.create('dnsrecords')
async def create_dnsrecords(spec, name, namespace, logger,bypass_rollout=False, **kwargs):
  provider = get_provider(namespace,spec.get('dnsServerRef'))
  if provider == "corednsFiles":
    return(await filednsoperator.create_dnsrecords(spec, name, namespace, logger,bypass_rollout=False, **kwargs))

@kopf.on.update('dnsrecords')
async def update_dnsrecords(spec, old, new, name, namespace, logger, diff, **_):
  provider = get_provider(namespace,spec.get('dnsServerRef'))
  if provider == "corednsFiles":
    return(await filednsoperator.update_dnsrecords(spec, old, new, name, namespace, logger, diff, **_))

@kopf.on.delete('dnsrecords')
async def delete_dnsrecords(spec, name, namespace, logger,bypass_rollout=False, **kwargs):
  provider = get_provider(namespace,spec.get('dnsServerRef'))
  if provider == "corednsFiles":
    return(await filednsoperator.delete_dnsrecords(spec, name, namespace, logger,bypass_rollout=False, **kwargs))

#config.load_kube_config()  # for local environment
#config.load_incluster_config()  