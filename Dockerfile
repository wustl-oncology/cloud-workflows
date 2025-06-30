FROM google/cloud-sdk:latest

RUN apt-get install -y zip

# Cloudize process
ADD scripts/cloudize-workflow.py /opt/scripts/cloudize-workflow.py
ADD scripts/pull_outputs.py /opt/scripts/pull_outputs.py
ADD scripts/requirements.txt /opt/scripts/requirements.txt
ADD scripts/validate_immuno_yaml.py /opt/scripts/validate_immuno_yaml.py

# Submit workflows
ADD scripts/submit_workflow.sh /opt/scripts/submit_workflow.sh

# Multi-approach help
ADD scripts/create_resources.sh /opt/scripts/create_resources.sh
ADD scripts/enable_api.sh /opt/scripts/enable_api.sh
ADD scripts/estimate_billing.py /opt/scripts/estimate_billing.py
ADD scripts/gb_estimate_billing.py /opt/scripts/gb_estimate_billing.py
ADD scripts/persist_artifacts.py /opt/scripts/persist_artifacts.py
ADD scripts/costs_json_to_csv.py /opt/scripts/costs_json_to_csv.py

# GMS setup/run
ADD gms/resources.sh /opt/gms/resources.sh
ADD gms/server_startup.py /opt/gms/server_startup.py
ADD gms/start.sh /opt/gms/start.sh

# Manual setup/run
ADD manual-workflows/base_cromwell.conf /opt/manual-workflows/base_cromwell.conf
ADD manual-workflows/helpers.sh /opt/manual-workflows/helpers.sh
ADD manual-workflows/resources.sh /opt/manual-workflows/resources.sh
ADD manual-workflows/user_permissions.sh /opt/manual-workflows/user_permissions.sh
ADD manual-workflows/server_startup.py /opt/manual-workflows/server_startup.py
ADD manual-workflows/start.sh /opt/manual-workflows/start.sh
ADD manual-workflows/cromwell.service /opt/manual-workflows/cromwell.service

RUN pip3 install --no-build-isolation --break-system-packages -r /opt/scripts/requirements.txt
