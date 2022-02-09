# built-in
import json
import os
import re
import requests
from argparse import ArgumentParser
from pathlib import Path
from subprocess import Popen, PIPE


DEFAULT_CROMWELL_URL = "http://34.69.35.61:8000"
DEFAULT_OUTPUTS_DIR = './outputs'
DEFAULT_DIR_STRUCTURE = 'FLAT'
DEFAULT_DRYRUN = False

# --- File system

def ensure_parent_dir_exists(filename):
    os.makedirs(filename.parent, exist_ok=True)


def file_extensions(path):
    "Extract all file extensions, e.g. 'foo.bam.bai' will return '.bam.bai'"
    return ".".join(path.split("/")[-1].split(".")[1:])


# --- Google Cloud Storage

def download_from_gcs(src, dest, dryrun=DEFAULT_DRYRUN):
    ensure_parent_dir_exists(dest)
    if not Path(dest).is_file():
        print(f"Downloading {src} to {dest}")
        if not dryrun:
            os.system(f"gsutil -q cp -n {src} {dest}")
    else:
        print(f"File already exists, skipping download {src} to {dest}")


# --- Cromwell server

def endpoint(hostname, route):
    return f"{hostname.strip('/')}/{route.strip('/')}"


def request_outputs(workflow_id, cromwell_url):
    """Requests the output file paths for a given workflow_id."""
    url = endpoint(cromwell_url, f'/api/workflows/v1/{workflow_id}/outputs')
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def flat_download(response, outputs_dir, dryrun=DEFAULT_DRYRUN):
    "Download outputs, using their output_name and file extension, not path structure."
    for k, gcs_loc in response['outputs'].items():
        output_name = k.split(".")[-1]
        if isinstance(gcs_loc, list):
            for loc in gcs_loc:
                filename = loc.split("/")[-1]
                download_from_gcs(loc, Path(f"{outputs_dir}/{output_name}/{filename}"), dryrun=dryrun)
        else:
            download_from_gcs(gcs_loc, Path(f"{outputs_dir}/{output_name}.{file_extensions(gcs_loc)}"), dryrun=dryrun)


def read_json(filename):
    if filename.startswith("gs://"):
        with Popen(['gsutil', 'cat', filename], stdout=PIPE, stderr=PIPE) as proc:
            contents = proc.stdout.read()
            if contents:
                return json.loads(contents)
            else:
                raise Exception(proc.stderr.read())
    else:
        with open(filename) as f:
            return json.load(f)


if __name__ == "__main__":
    parser = ArgumentParser(description="Download Cromwell outputs for a given workflow.")
    parser.add_argument("--workflow-id",
                        help="the UUID of the workflow run to pull outputs for. Exclusive with outputs_file")
    parser.add_argument("--outputs-file",
                        help="JSON file of workflow outputs to pull. Exclusive with workflow_id.")
    parser.add_argument("--outputs-dir",
                        help=f"directory path to download outputs to. Defaults to {DEFAULT_OUTPUTS_DIR}")
    parser.add_argument("--cromwell-url",
                        help=f"URL of the relevant Cromwell server. Honors env var CROMWELL_URL. Defaults to {DEFAULT_CROMWELL_URL}")
    parser.add_argument("--dryrun",
                        help=f"If this arg is set to True, skips the actual download and just prints progress info. Useful for troubleshooting the script. Defaults to {DEFAULT_DRYRUN}")
    args = parser.parse_args()

    dryrun = args.dryrun or DEFAULT_DRYRUN

    outputs_dir = args.outputs_dir or DEFAULT_OUTPUTS_DIR
    cromwell_url = args.cromwell_url or os.environ.get('CROMWELL_URL', DEFAULT_CROMWELL_URL)

    if args.workflow_id and args.outputs_file:
        raise Exception("must specify only one of --workflow-id and --outputs-file")
    elif args.workflow_id:
        outputs = request_outputs(args.workflow_id, cromwell_url)
        outputs_dir = f"{outputs_dir}/{args.workflow_id}"
    elif args.outputs_file:
        outputs = read_json(args.outputs_file)
    else:  # not (workflow_id or outputs_file):
        raise Exception("must specify either --workflow-id or --outputs-file")

    flat_download(outputs, outputs_dir, dryrun=dryrun)
