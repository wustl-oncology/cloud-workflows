FROM google/cloud-sdk:latest

RUN apt-get install -y zip
COPY requirements.txt /opt/requirements.txt
RUN pip3 install -r /opt/requirements.txt
COPY cloudize-workflow.py /opt/cloudize-workflow.py
COPY pull_outputs.py /opt/pull_outputs.py
COPY submit_workflow.sh /opt/submit_workflow.sh
