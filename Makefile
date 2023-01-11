SHELL:=/bin/bash
NAMESPACE=dns-operator
docker-image: Dockerfile
	docker build -t davidp1404/dns-operator .
	kind load docker-image davidp1404/dns-operator # for my k8s setup based on kind

yaml-stanzas:
	mkdir -p yaml
	kubectl create ns ${NAMESPACE} --dry-run=client -o yaml > yaml/namespace.yaml
	kubectl -n ${NAMESPACE} create sa dns-operator-sa --dry-run=client -o yaml > yaml/dns-operator-sa.yaml
	kubectl create cm dns-operator-app --from-file=dns-operator.py=src/dns-operator.py \
	--from-file=filednsoperator.py=src/filednsoperator.py --dry-run=client -o yaml > yaml/dns-operator-app.yaml
	kubectl create cm dns-operator-templates --from-file=src/templates --dry-run=client -o yaml > yaml/dns-operator-templates.yaml

install-crds:
	kubectl apply -f crds/dns-operator-crds.yaml
	kubectl apply -f crds/kopf-peering.yaml
	@sleep 2
	kubectl apply -f crds/kopf-peering-id.yaml

uninstall-crds:
	-@read -n1 -p "Delete all dnss and dnsr to avoid orphans? (ctrl+c to stop)" && kubectl delete dnss,dnsr -A --all 
	kubectl delete -f crds/dns-operator-crds.yaml
	kubectl delete -f crds/kopf-peering.yaml

install-operator: yaml-stanzas
	kubectl kustomize yaml | kubectl apply -f -

uninstall-operator:
	kubectl kustomize yaml | kubectl delete -f -

install-qasamples:
	cat qa/{server,record}*.yaml | kubectl -n default apply -f -

uninstall-qasamples:
	cat qa/{server,record}*.yaml | kubectl -n default delete -f -

validate:
	@(dig +short @172.18.255.201 record1.sample.org | grep "10.0.0.1" > /dev/null && echo "record1: ok" || echo "record1: fail")
	@(dig +short @172.18.255.201 record2.sample.org | sort | grep -Pzo -e "10.0.0.1\n10.0.0.3" > /dev/null && echo "record2: ok" || echo "record2: fail") 
	@(dig +short @172.18.255.201 -x 10.0.0.3 | grep "record3.sample.org." > /dev/null && echo "record3: ok" || echo "record3: fail") 
	@(dig +short @172.18.255.201 -x 10.0.0.4 | grep "record4.sample.org." > /dev/null && echo "record4: ok" || echo "record4: fail") 
	@(dig +short @172.18.255.201 -x 10.0.0.5 | grep "record5.sample.org." > /dev/null && echo "record5: ok" || echo "record5: fail")
	@(dig +short @172.18.255.201 record6.sample.org | sort | grep -Pzo -e "10.0.0.1\nrecord1.sample.org." > /dev/null && echo "record6: ok" || echo "record6: fail")
	@(dig +short @172.18.255.201 aaaa record7.sample.org grep "2002:7f00:0:1::1" > /dev/null && echo "record7: ok" || echo "record7: fail")
	@(dig +short @172.18.255.201 -x 2002:7f00:0:1::1 | grep "record8.sample.org." > /dev/null && echo "record8: ok" || echo "record8: fail")

stress:
	@while true;do for r in {2..8};do kubectl delete -f qa/record$${r}.yaml;done;for r in {2..8};do kubectl create -f qa/record$${r}.yaml;done;done
