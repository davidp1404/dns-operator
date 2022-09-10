SHELL:=/bin/bash
NAMESPACE=dns-operator
docker-image: Dockerfile
	docker build -t davidp1404/dns-operator .
	kind load docker-image davidp1404/dns-operator # for my k8s setup based on kind

yaml-stanzas:
	mkdir -p yaml
	kubectl create ns ${NAMESPACE} --dry-run=client -o yaml > yaml/namespace.yaml
	kubectl -n ${NAMESPACE} create sa dns-operator-sa --dry-run=client -o yaml > yaml/dns-operator-sa.yaml
	kubectl create cm dns-operator-app --from-file=dns-operator.py=src/dns-operator.py --dry-run=client -o yaml > yaml/dns-operator-app.yaml
	kubectl create cm dns-operator-templates --from-file=src/templates --dry-run=client -o yaml > yaml/dns-operator-templates.yaml

install-crds:
	kubectl apply -f crds/dns-operator-crds.yaml
	kubectl apply -f crds/kopf-peering.yaml

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


