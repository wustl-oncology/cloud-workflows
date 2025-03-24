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


# Using a decorator to reduce logging annoyances
# Referenced this guide for construction:
# https://www.thecodeship.com/patterns/guide-to-python-function-decorators/
def bookends(print_func):
    """
    Print using `print_func` the `body_func`'s name and args at start and completion of function.
    """
    def decorator(body_func):
        def wrapper(*args, **kwargs):
            print_func(f"{body_func.__name__} {args} {kwargs} ...")
            result = body_func(*args, **kwargs)
            print_func(f"{body_func.__name__} {args} {kwargs} ...DONE")
            return result
        return wrapper
    return decorator


@bookends(logging.info)
def install_packages():
    """
    Install required system packages and required python packages.
    """
    os.system('apt-get update')
    os.system('apt-get install -y ' + ' '.join([
        'curl',
        'default-jdk',
        'python3-pip'
    ]))
    os.system('python3 -m pip install "requests>=2.20.0"')


@bookends(logging.info)
def install_cromwell(version):
    """
    Fetches Cromwell jar for `version` and writes it locally to `CROMWELL_JAR`.
    """
    import requests
    url = f"https://github.com/broadinstitute/cromwell/releases/download/{version}/cromwell-{version}.jar"
    response = requests.get(url)
    if not response.ok:
        raise Exception("GET failed for {}".format(url))
    with open(CROMWELL_JAR, "wb") as f:
        f.write(response.content)


@bookends(logging.debug)
def write_from_metadata(tag, dest_path):
    """
    Writes contents of `tag` to `dest_path`.
    """
    with open(dest_path, 'w') as f:
        f.write(_fetch_instance_attribute(tag))


@bookends(logging.debug)
def download_from_metadata(tag, dest_path):
    """
    Download gs:// path from `tag` to `dest_path`. `tag` value expected to be a GCS path.
    """
    os.system(f"gsutil cp {_fetch_instance_attribute(tag)} {dest_path}")


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


@bookends(logging.info)
def start_cromwell_service():
    """
    Starts Cromwell as a systemd service.

    Blocks until service has completed startup. Throws on failure to start.
    """
    os.system('systemctl daemon-reload')
    os.system('systemctl start cromwell.service')
    assert wait_until_cromwell_start()


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


@bookends(logging.debug)
def persist_vm_logs(gcs_dir):
    """
    Write startup script logs to GCS.

    We want this to troubleshoot issues since the VM dies.
    This won't help when there are issues with uploading to bucket, though..
    """
    os.system('journalctl -u google-startup-scripts > vm.log')
    os.system('journalctl -u cromwell > cromwell.log')
    os.system(f"gsutil cp vm.log {gcs_dir}/vm.log")
    os.system(f"gsutil cp cromwell.log {gcs_dir}/cromwell.log")


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
    logging.debug("Destroying VM")
    zone = _fetch_instance_metadata('zone').split('/')[-1]
    hostname = socket.gethostname()
    os.system(f"gcloud compute instances delete {hostname} --zone={zone} -q")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='python[%(levelname)s] %(message)s'
    )

    install_packages()
    logging.info("Packages installed.")

    os.makedirs(CROMWELL_DIR, exist_ok=True)

    # Pull required parameters from instance tags.
    #
    # These are outside the try because they're required by the
    # finally.  If failure occurs before the try, auto-shutdown and
    # log persistence won't happen and troubleshooting must be done
    # via SSH.
    bucket = _fetch_instance_attribute('bucket')
    build = _fetch_instance_attribute('build-id')
    outdir = f"gs://{bucket}/build.{build}"
    auto_shutdown = bool(_fetch_instance_attribute('auto-shutdown'))

    try:
        cromwell_version = _fetch_instance_attribute('cromwell-version')
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
        logging.debug(f"Received response {response}")
        response.raise_for_status()
        workflow_id = response.json()['id']
        logging.info(f"Began workflow {workflow_id}")

        # spin until workflow stops running (yuck)
        status = wait_for_workflow_to_run(workflow_id)
        logging.info(f"Final status is {status}")

        # Persist artifacts
        #
        # This current approach will overwrite previous artifacts if
        # the same build is re-ran. If this is a problem then we can
        # come back and add a separate identifier to store
        # them. workflow_id WON'T work because that value isn't
        # exposed to GMS. Probably will have to have GMS create that
        # identifier and pass in as attribute.
        persist_url_response(f"{CROMWELL_URL}/{workflow_id}/timing", outdir, 'timing.html')
        logging.info("Persisted timing.html")
        if status == "Succeeded":
            persist_url_response(f"{CROMWELL_URL}/{workflow_id}/outputs", outdir, 'outputs.json')
            logging.info("Persisted outputs.json")

        # Shut down
        logging.info("Startup script...DONE")
    except Exception as e:
        logging.error(e)
    finally:
        logging.debug("Wrapping up")
        # VM logs persisted to GCS to enable troubleshooting when
        # instance self-destructs or in case where SSH is disabled.
        # Will NOT be persisted if there is an issue with the
        # bucket. This case will require starting with auto_shutdown
        # flag disabled, ssh in and check `journalctl google-startup-scripts`
        persist_vm_logs(outdir)
        if auto_shutdown:
            self_destruct_vm()
