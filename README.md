# dns-operator
Kubernetes DNS operator based on coredns and developed with python3 using [kubernetes](https://github.com/kubernetes-client/python) and [kopf](https://kopf.readthedocs.io/en/stable/) libraries.     
Currently it only supports coredns files (a configmap) as the backing storage using jinja2 templates to render config files. It could be easily adapted to use other backends due to the flexibility of coredns, being straightforward to connect with public cloud DNS services. 
## What it does?
Extend kubernetes api with new CRDs to allow you:
1) Manage DNS instances (create/delete):
```
$ cat qa/server-sample.yaml 
---
apiVersion: davidp1404.github.com/v1
kind: dnsServer
metadata:
  name: sample.org
  namespace: default
spec:
  zones: 
  - sample.org
  - 0.0.10.in-addr.arpa
  replicas: 2

$ kubectl create -f qa/server-sample.yaml
dnsserver.davidp1404.github.com/sample.org created

$ kubectl get cm,deployment,svc -l app.kubernetes.io/managed-by="dns-operator"
NAME                                DATA   AGE
configmap/dns-operator-sample-org   3      137m

NAME                                      READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/dns-operator-sample-org   2/2     2            2           137m

NAME                                  TYPE           CLUSTER-IP     EXTERNAL-IP      PORT(S)        AGE
service/dns-operator-tcp-sample-org   LoadBalancer   10.96.118.22   172.18.255.201   53:30366/TCP   137m
service/dns-operator-udp-sample-org   LoadBalancer   10.96.72.49    172.18.255.201   53:30833/UDP   137m

$ k get dnss
NAME         PROVIDER       ZONES                                  REPLICAS   AGE
sample.org   corednsFiles   ["sample.org","0.0.10.in-addr.arpa"]   2          141m

```
2) Manage DNS records (create/delete/update):

```
$ cat qa/record{1,3}.yaml 
---
apiVersion: davidp1404.github.com/v1
kind: dnsRecord
metadata:
  name: record1
  namespace: default
spec:
  dnsServerRef: sample.org
  recordType: A
  zone: sample.org
  recordKey: "record1"
  recordValue: ["10.0.0.2"]
---
apiVersion: davidp1404.github.com/v1
kind: dnsRecord
metadata:
  name: record3
  namespace: default
spec:
  dnsServerRef: sample.org
  recordType: PTR
  zone: 0.0.10.in-addr.arpa
  recordKey: "3"
  recordValue: ["record3.sample.org."]
  
$ cat qa/record{1,3}.yaml | kubectl create -f -
dnsrecord.davidp1404.github.com/record1 created
dnsrecord.davidp1404.github.com/record3 created

$ k get dnsr
NAME      ZONE                  KEY       TYPE   VALUE                     TTL   AGE
record1   sample.org            record1   A      ["10.0.0.2"]              5     19s
record3   0.0.10.in-addr.arpa   3         PTR    ["record3.sample.org."]   5     19s
```
## Installation:
```
$ git clone --depth 1 --branch v1.0 https://github.com/davidp1404/dns-operator.git
$ cd dns-operator
# Tune the docker-image defintion in the Makefile to reflect your scenario
# Modify yaml/dns-operator-deployment.yaml file with the image url/tag chosen 
# Ensure your kubeconfig/context grants you the privileges needed to create crds, clusterroles, clusterrolebindings, serviceaccounts, configmaps, deployments
$ make docker-image
$ make install-crd
$ make install-operator
$ make install-qasamples
```
By defatul the services were tuned for metal-lb, but you can adapt them to your specific use case editing the configmap with the jinja2 templates. 
```
$ kubectl -n dns-operator get cm dns-operator-templates -o json | jq -r '.data."service-tcp.j2"'
apiVersion: v1
kind: Service
metadata:
  name: dns-operator-tcp-{{name}}
  namespace: {{namespace}}
  labels:
    app: dns-operator-{{name}}
    app.kubernetes.io/managed-by: "dns-operator"
  annotations:
    metallb.universe.tf/allow-shared-ip: dns-operator-{{name}}
spec:
  selector:
    app: dns-operator-{{name}}
  type: {{lbtype}}
  sessionAffinity: None
  ports:
  - name: dnstcp
    protocol: TCP
    port: 53
    targetPort: 1053
$ kubectl -n dns-operator get cm dns-operator-templates -o json | jq -r '.data."service-udp.j2"'
apiVersion: v1
kind: Service
metadata:
  name: dns-operator-udp-{{name}}
  namespace: {{namespace}}
  labels:
    app: dns-operator-{{name}}
    app.kubernetes.io/managed-by: "dns-operator"
  annotations:
    metallb.universe.tf/allow-shared-ip: dns-operator-{{name}}
spec:
  selector:
    app: dns-operator-{{name}}
  type: {{lbtype}}
  sessionAffinity: None
  ports:
  - name: dnstcp
    protocol: UDP
    port: 53
    targetPort: 1053
```
## Uninstallation
```
$ make uninstall-crd
$ make uninstall-operator
$ make uninstall-qasamples
```

## Status:
Maturity: early beta   
Limitations:
- [ ] You can't change a DNS instance, only create or delete
- [ ] Develop an admission controller to disable updated verbs in dsnServers crds

## Pending:
- [x] Makefile to create docker images and install
- [x] Operator with multiple replicas 
- [x] Package with kustomize
- [x] Enable ipv6
- [ ] Enable managing of optional forward directives (currently only resolve for authoritative zones)
- [ ] Reload all present records after recreating a dns instance
- [ ] Improving QA tests (pytest)
- [ ] Package with helm
- [x] Refactor with python modules to encapsulate multiple backend providers.
- [ ] Add support to manage cloud dns services (route53/AWS, Azure DNS, Google Cloud DNS)

