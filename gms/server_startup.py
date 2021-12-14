#!/usr/bin/env python3

import datetime
import logging
import os
import socket
import subprocess
import sys
import time

# auto-shutdown
# cromwell-conf
# cromwell-service
# workflow-wdl
# inputs-yaml
# deps-zip
# options-json
# cromwell-version

CROMWELL_URL = "http://localhost:8000/api/workflows/v1"
CROMWELL_DIR = os.path.join(os.path.sep, 'opt', 'cromwell')

# Required file paths
CROMWELL_SERVICE =  os.path.join(os.path.sep, 'etc', 'systemd', 'system', 'cromwell.service')
CROMWELL_CONF = os.path.join(CROMWELL_DIR, 'cromwell.conf')
CROMWELL_JAR  = os.path.join(CROMWELL_DIR, 'cromwell.jar')
DEPS_ZIP      = os.path.join(CROMWELL_DIR, 'workflow_deps.zip')
INPUTS_YAML   = os.path.join(CROMWELL_DIR, 'inputs.yaml')
OPTIONS_JSON  = os.path.join(CROMWELL_DIR, 'options.json')
WORKFLOW_WDL  = os.path.join(CROMWELL_DIR, 'workflow.wdl')


def install_packages():
    """
    Install required system packages and required python packages.
    """
    logging.info("Install packages...")
    os.system('apt-get update')
    os.system('apt-get install -y ' + ' '.join([
        'curl',
        'default-jdk',
        'python3-pip'
    ]))
    os.system('python3 -m pip install requests>=2.20.0')
    logging.info("Install packages... DONE")


def install_cromwell(version):
    """
    Fetches Cromwell jar for `version` and writes it locally to `CROMWELL_JAR`.
    """
    logging.info(f"Installing cromwell version {version} at {CROMWELL_JAR}...")
    import requests
    url = f"https://github.com/broadinstitute/cromwell/releases/download/{version}/cromwell-{version}.jar"
    response = requests.get(url)
    if not response.ok:
        raise Exception("GET failed for {}".format(url))
    with open(CROMWELL_JAR, "wb") as f:
        f.write(response.content)
    logging.info(f"Installing cromwell version {version} at {CROMWELL_JAR}...DONE")


def write_from_metadata(tag, dest_path):
    """
    Writes contents of `tag` to `dest_path`.
    """
    logging.debug(f"Write {tag}...")
    with open(dest_path, 'w') as f:
        f.write(_fetch_instance_attribute(tag))
    logging.debug(f"Write {tag}...DONE")


def download_from_metadata(tag, dest_path):
    """
    Download gs:// path from `tag` to `dest_path`. `tag` value expected to be a GCS path.
    """
    logging.debug(f"Download {tag}...")
    os.system(f"gsutil cp {_fetch_instance_attribute(tag)} {dest_path}")
    logging.debug(f"Download {tag}...DONE")


def _fetch_instance_metadata(path):
    """
    Requests data about the hosting Google compute instance.
    """
    import requests
    url = f"http://metadata.google.internal/computeMetadata/v1/instance/{path}"
    response = requests.get(url, headers={'Metadata-Flavor': 'Google'})
    if not response.ok:
        raise Exception("GET failed for {}".format(url))
    return response.text


def _fetch_instance_attribute(name):
    return _fetch_instance_metadata(f"attributes/{name}")


def start_cromwell_service():
    """
    Starts Cromwell as a systemd service.

    Blocks until service has completed startup. Throws on failure to start.
    """
    logging.info("Start cromwell service...")
    os.system('systemctl daemon-reload')
    os.system('systemctl start cromwell.service')
    assert wait_until_cromwell_start()
    logging.info("Start cromwell service...DONE")


def wait_until_cromwell_start():
    """
    Blocking call until Cromwell service outputs either started or shutdown message.
    """
    ps = subprocess.Popen(
        ['journalctl', '-u', 'cromwell', '-f'],
        stdout=subprocess.PIPE,
        text=True
    )
    ret_val = None
    logging.info("Waiting for Cromwell service to start...")
    while True:
        output = ps.stdout.readline()
        if ps.poll() is not None:
            break

        if 'service started' in output:
            logging.info("Cromwell service has started")
            return True
        elif 'Shutting down' in output:
            logging.info("Cromwell service FAILED to start. Shutting down.")
            return False
        else:
            logging.debug(output.rstrip())
    return False


def wait_for_workflow_to_run(workflow_id):
    """
    Poll workflow status until not Running or Submitted, i.e. no longer in progress.

    Returns final status when polling stops.
    """
    status = None
    while not status or status == "Running" or status == "Submitted":
        time.sleep(30)
        response = requests.get(f"{CROMWELL_URL}/{workflow_id}/status")
        response.raise_for_status()
        status = response.json()['status']
        logging.info(f"Polled workflow {workflow_id}. Status : {status}")
    return status


def persist_vm_logs(gcs_dir):
    """
    Write startup script logs to GCS.

    We want this to troubleshoot issues since the VM dies.
    This won't help when there are issues with uploading to bucket, though..
    """
    timestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
    os.system('journalctl -u google-startup-scripts > vm.log')
    os.system(f"gsutil cp vm.log {gcs_dir}/vm_{timestamp}.log")


def persist_url_response(url, gcs_dir, filename):
    """
    GET a `url`, write response contents to `filename`, and upload that to `gcs_dir`.
    """
    response = requests.get(url)
    if response.ok:
        logging.debug(f"Persisting {filename}")
        with open(filename, 'wb') as f:
            f.write(response.content)
        os.system(f"gsutil cp {filename} {outdir}/{filename}")
    else:
        # TODO(john): troubleshooting info from response
        logging.error(f"Could not retrieve {filename} diagram. Please investigate")


def self_destruct_vm():
    """
    Deletes the hosting instance.
    Instances are created automatically and need to be deleted on completion.
    """
    zone = _fetch_instance_metadata('zone').split('/')[-1]
    hostname = socket.gethostname()
    os.system(f"gcloud compute instances delete {hostname} --zone={zone} -q")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='python[%(levelname)s] %(message)s'
    )

    install_packages()
    logging.info("Packages installed.")

    os.makedirs(CROMWELL_DIR, exist_ok=True)

    # Pull required parameters from instance tags
    bucket = _fetch_instance_attribute('bucket')
    build = _fetch_instance_attribute('build-id')
    cromwell_version = _fetch_instance_attribute('cromwell-version')
    auto_shutdown = bool(_fetch_instance_attribute('auto-shutdown'))

    try:
        # Pull required files from instance tags
        write_from_metadata('cromwell-conf', CROMWELL_CONF)
        write_from_metadata('cromwell-service', CROMWELL_SERVICE)
        write_from_metadata('workflow-wdl', WORKFLOW_WDL)  # max size 256k before download
        write_from_metadata('inputs-yaml', INPUTS_YAML)    # max size 256k before download
        write_from_metadata('options-json', OPTIONS_JSON)  # max size 256k before download
        download_from_metadata('deps-zip', DEPS_ZIP)

        # Run Cromwell service
        install_cromwell(cromwell_version)
        logging.info(f"Cromwell {cromwell_version} installed.")

        start_cromwell_service()
        logging.info("Cromwell service started.")

        # Submit workflow
        import requests
        logging.debug("POSTing request for workflow submission")
        response = requests.post(
            f"{CROMWELL_URL}",
            files={'workflowSource':       open(WORKFLOW_WDL, 'rb'),
                   'workflowInputs':       open(INPUTS_YAML, 'rb'),
                   'workflowDependencies': open(DEPS_ZIP, 'rb'),
                   'workflowOptions':      open(OPTIONS_JSON, 'rb')}
        )
        response.raise_for_status()
        workflow_id = response.json()['id']
        logging.info(f"Began workflow {workflow_id}")

        # spin until workflow stops running (yuck)
        status = wait_for_workflow_to_run(workflow_id)
        logging.info(f"Final status is {status}")

        # Persist artifacts
        outdir = f"gs://{bucket}/build.{build}/workflow.{workflow_id}"
        persist_url_response(f"{CROMWELL_URL}/{workflow_id}/timing", outdir, 'timing.html')
        logging.info("Persisted timing.html")
        if status == "Succeeded":
            persist_url_response(f"{CROMWELL_URL}/{workflow_id}/outputs", outdir, 'outputs.json')
            logging.info("Persisted outputs.json")

        # Shut down
        logging.info("Startup script...DONE")

    finally:
        persist_vm_logs(f"gs://{bucket}/build.{build}")
        if auto_shutdown:
            self_destruct_vm()
