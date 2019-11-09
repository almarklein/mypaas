# mypaas web service
#
# mypaas.service=deployer
# mypaas.domain=almarklein.com
# mypaas.volume=/root/_deploys:/deploys
# mypaas.port=80

FROM python:3.7-alpine

RUN apk update
RUN pip --no-cache-dir install click h11 \
    && pip --no-cache-dir install uvicorn==0.6.1 --no-deps \
    && pip --no-cache-dir install asgineer==0.7.1

COPY . .
CMD python deploy_service.py

