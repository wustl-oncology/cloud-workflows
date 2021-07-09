FROM python:3.8

COPY requirements.txt /opt/requirements.txt
RUN pip3 install -r /opt/requirements.txt
COPY cloudize-workflow.py /opt/cloudize-workflow.py
COPY pull_outputs.py /opt/pull_outputs.py
