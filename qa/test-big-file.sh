for r in {10..100}
do
    cat <<EOF | kubectl $1 -f -
---
apiVersion: davidp1404.github.com/v1
kind: dnsRecord
metadata:
  name: record${r}
  namespace: default
spec:
  dnsServerRef: sample.org
  recordType: A
  zone: sample.org
  recordKey: "record${r}"
  recordValue: ["10.0.0.${r}"]
EOF
done