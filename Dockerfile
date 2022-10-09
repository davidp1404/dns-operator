FROM python:3.7-alpine
RUN mkdir -p /app/templates &&\
    addgroup -S dns-operator &&\
    adduser dns-operator -S -u 1000  -G dns-operator -h /app &&\
    chown -R dns-operator:dns-operator /app
COPY requirements.txt /app
WORKDIR /app
RUN pip install -r requirements.txt
USER dns-operator
CMD kopf run -A --peering=dns-operator /app/dns-operator.py 
