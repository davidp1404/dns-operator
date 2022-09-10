FROM python:3.7-alpine
RUN mkdir -p /app/templates &&\
    addgroup -S dns-operator &&\
    adduser -S dns-operator -G dns-operator -h /app &&\
    chown -R dns-operator:dns-operator /app
COPY requirements.txt /app
WORKDIR /app
RUN pip install -r requirements.txt
USER dns-operator
CMD kopf run -A /app/dns-operator.py 
