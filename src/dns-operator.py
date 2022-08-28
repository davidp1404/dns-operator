
def genDNSDeployment(name,namespace,zoneList):
    deploymentTemplate="""
apiVersion: apps/v1
kind: Deployment
metadata:
  name:  {name}
  namespace: {namespace}
  labels:
    managed-by: "dns-operator"
spec:
  selector:
    matchLabels:
      app: {name}
  replicas: 2
  strategy:
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 50%
    type: RollingUpdate
  template:
    metadata:
      labels:
        managed-by: "dns-operator"
        app: {name} 
    spec:
      containers:
      - name:  main
        image: k8s.gcr.io/coredns/coredns:v1.8.4
        args:
        - -dns.port
        - "1053"
        - -conf
        - /etc/coredns/Corefile
        env:
        - name: TZ
          value: "Europe/Madrid"
        resources:
          requests:
            cpu: 250m
            memory: 250Mi
          limits:
            cpu: 250m
            memory: 250Mi
        livenessProbe:
          failureThreshold: 5
          httpGet:
            path: /health
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 60
          periodSeconds: 10
          successThreshold: 1
          timeoutSeconds: 5
        readinessProbe:
          failureThreshold: 3
          httpGet:
            path: /ready
            port: 8181
            scheme: HTTP
          periodSeconds: 10
          successThreshold: 1
          timeoutSeconds: 1
        ports:
        - containerPort: 1053
          name: dns
          protocol: UDP
        - containerPort: 1053
          name: dns-tcp
          protocol: TCP
        - containerPort: 9153
          name: metrics
          protocol: TCP
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
        volumeMounts:
        - mountPath: /etc/coredns
          name: config-volume
          readOnly: true
      restartPolicy: Always
      volumes:
      - name: config-volume
        configMap:
          name: {name}
          items:
          - key: Corefile
            path: Corefile
"""
    body=(deploymentTemplate.format(namespace=namespace,name=name))
    for zone in zoneList:
        body += f"          - key: db.{zone}\n            path: db.{zone}\n"
    return(body)    

def genDNSConfigmap (name,namespace,zoneList):
    configmapTemplate = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: {name}
data:
  Corefile: |
    .:1053 {{
      root /etc/coredns
      errors
      health
      ready
      prometheus :9153
      reload 2s 1s
      log"""
    corefileTemplate = """
      file db.{zone} {zone} {{
        reload 2s
      }}"""

    zoneDefTemplate = """
  db.{zone}: |
    $ORIGIN {zone}.
    @   3600 IN SOA sns.dns.icann.org. noc.dns.icann.org. (
            2017042761 ; serial
            7200       ; refresh (2 hours)
            3600       ; retry (1 hour)
            1209600    ; expire (2 weeks)
            3600       ; minimum (1 hour)
            )
        3600 IN NS a.iana-servers.net.
        3600 IN NS b.iana-servers.net."""
    body = configmapTemplate.format(name=name)
    zonelistString = ""
    for zone in zoneList:
        body += corefileTemplate.format(zone=zone)
        zonelistString += " db." + zone
    body += """
      auto {zonelistString} {{
        reload 2s
      }}
    }}""".format(zonelistString=zonelistString)

    for zone in zoneList:
        body += zoneDefTemplate.format(zone=zone)

    return(body)


deployment = genDNSDeployment("dnsinstance01","default",["example.org", "0.0.10.in-addr.arpa"])
configmap = genDNSConfigmap("dnsinstance01","default",["example.org", "0.0.10.in-addr.arpa"])

print(deployment+"\n---\n"+configmap)
