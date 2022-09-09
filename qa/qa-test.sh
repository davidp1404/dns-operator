#!/bin/bash
for file in {1..6}
do
    kubectl create -f record$file.yaml
    sleep 0.2
    kubectl get cm dns-operator-sample-org -o yaml | grep record$file
    sleep 0.2
    kubectl delete -f record$file.yaml
done
