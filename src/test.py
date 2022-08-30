import os
import kopf
import kubernetes
import yaml
import json

@kopf.on.create('dnsservers')
def create_fn(spec, name, namespace, logger, **kwargs):
    print(spec)
    # size = spec.get('size')
    # if not size:
    #     raise kopf.PermanentError(f"Size must be set. Got {size!r}.")

    # path = os.path.join(os.path.dirname(__file__), 'pvc.yaml')
    # tmpl = open(path, 'rt').read()
    # text = tmpl.format(name=name, size=size)
    # data = yaml.safe_load(text)

    # api = kubernetes.client.CoreV1Api()
    # obj = api.create_namespaced_persistent_volume_claim(
    #     namespace=namespace,
    #     body=data,
    # )

    logger.info(f"CRD is created: {name}")
    cm=yaml.dump(['example.org','0.0.10.in-addr.arpa'],default_flow_style=True,default_style='"')

    return { 'deploymentRef': f'dep-{name}', 'configMapRefs': f'{cm}' }



@kopf.on.update('dnsservers')
def update_fn(spec, status, namespace, logger, **kwargs):
    for msg in json.loads(status['create_fn']['configMapRefs']):
        logger.info(f"Updating: {msg}")