#!/bin/bash

start() {
    source ~/.venv/bin/activate
    clear
    kopf run -A --priority 100 src/dns-operator.py
}

qa-run() {
    cat qa/{server,record}*.yaml | kubectl create -f -
    kubectl get dnss,dnsr
}

qa-clean() {
    cat qa/{server,record}*.yaml | kubectl delete -f -
    kubectl get dnss,dnsr
}

qa-check() {
    kubectl get dnss,dnsr
    kubectl get cm dns-operator-sample-org -o yaml | grep record
}


"$@"
