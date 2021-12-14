FROM google/cloud-sdk:latest

RUN apt-get install -y zip

ADD scripts/cloudize-workflow.py /opt/scripts/cloudize-workflow.py
ADD scripts/pull_outputs.py /opt/scripts/pull_outputs.py
ADD scripts/requirements.txt /opt/scripts/requirements.txt
ADD scripts/workflow_options_bolton.json /opt/scripts/workflow_options_bolton.json
ADD scripts/workflow_options_griffith.json /opt/scripts/workflow_options_griffith.json
ADD scripts/submit_workflow.sh /opt/scripts/submit_workflow.sh

ADD gms/resources.sh /opt/gms/resources.sh
ADD gms/server_startup.py /opt/gms/server_startup.py
ADD gms/start.sh /opt/gms/start.sh

ADD manual-workflows/base_cromwell.conf /opt/manual-workflows/base_cromwell.conf
ADD manual-workflows/helpers.sh /opt/manual-workflows/helpers.sh
ADD manual-workflows/resources.sh /opt/manual-workflows/resources.sh
ADD manual-workflows/server_startup.py /opt/manual-workflows/server_startup.py
ADD manual-workflows/start.sh /opt/manual-workflows/start.sh

RUN pip3 install -r /opt/scripts/requirements.txt
