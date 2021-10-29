FROM google/cloud-sdk:latest

RUN apt-get install -y zip

ADD scripts /opt/scripts
ADD manual-workflows /opt/manual-workflows

RUN pip3 install -r /opt/scripts/requirements.txt
