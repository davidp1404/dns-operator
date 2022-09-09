# dns-operator
Kubernetes DNS operator based on coredns and developed with python3 using [kubernetes](https://github.com/kubernetes-client/python) and [kopf](https://kopf.readthedocs.io/en/stable/) libraries.     
Currently it only supports coredns files (a configmap) as the backing storage using jinja2 templates to render config files. It could be easily adpated to use other backends due to the flexibility of coredns, being straightforward to connect with public cloud DNS services. 
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
## Status:
Maturity: early beta   
Limitations:
- [ ] You can't change a DNS instance, only create or delete

## Pending:
- [x] Operator with multiple replicas 
- [ ] Reload all present records after recreating a dns instance
- [ ] Makefile to create docker images and install
- [ ] Improving QA tests (pytest)
- [ ] Package with helm and kustomize
- [ ] Add support to manage cloud dns services (route53/AWS, Azure DNS, Google Cloud DNS)

