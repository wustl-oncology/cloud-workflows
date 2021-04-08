# third-party, pip install
from google.cloud import storage
# built-in
import os
import re
import requests
from argparse import ArgumentParser
from pathlib import Path

DEFAULT_CROMWELL_URL = "http://34.69.35.61:8000"
DEFAULT_OUTPUT_DIR = './outputs'

GCS = storage.Client()

# --- Local file system

def ensure_parent_dir_exists(filename):
    os.makedirs(filename.parent, exist_ok=True)

# --- Google Cloud Storage

GCS_URI = r'gs:\/\/([^\/]+)\/(.+)'

def bucket_name(gcs_uri):
    return re.search(GCS_URI, gcs_uri).group(1)

def storage_object_name(gcs_uri):
    return re.search(GCS_URI, gcs_uri).group(2)


def download_from_gcs(src, dest):
    ensure_parent_dir_exists(dest)
    GCS.bucket(bucket_name(src)).blob(storage_object_name(src)).download_to_filename(dest)
    print(f"Downloaded {src} to {dest}")

# --- Cromwell server

def request_outputs(workflow_id, cromwell_url):
    """Requests the output file paths for a given workflow_id."""
    url = f"{cromwell_url}/api/workflows/v1/{workflow_id}/outputs"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def extract_file_locations(outputs_response):
    """Parse an outputs_response map, extracting primary and secondary output file locations."""
    primary_files = [output['location'] for k, output in outputs_response['outputs'].items()]
    secondary_files = [sf['location']
                       for k, output in outputs_response['outputs'].items()
                       if output['secondaryFiles']
                       for sf in output['secondaryFiles']]
    return primary_files + secondary_files

# --- Do the download

def download_locations(output_dir, gcs_locations):
    return [Path(f"{output_dir}/{Path(loc).parent.stem}/{Path(loc).name}") for loc in gcs_locations]


def download_outputs(workflow_id, output_dir, cromwell_url):
    response = request_outputs(workflow_id, cromwell_url)
    gcs_locations = extract_file_locations(response)
    for src, dest in zip(gcs_locations, download_locations(output_dir, gcs_locations)):
        download_from_gcs(src, dest)


if __name__=="__main__":
    parser = ArgumentParser(description="Download Cromwell outputs for a given workflow.")
    parser.add_argument("workflow_id", help="the UUID of the workflow run to pull outputs for.")
    parser.add_argument("-o", "--output",
                        help="directory path to download outputs to. Defaults to {DEFAULT_OUTPUT_DIR}")
    parser.add_argument("--cromwell-url",
                        help=f"URL of the relevant Cromwell server. Defaults to {DEFAULT_CROMWELL_URL}")
    args = parser.parse_args()

    output_dir = args.output or DEFAULT_OUTPUT_DIR
    cromwell_url = args.cromwell_url or DEFAULT_CROMWELL_URL

    download_outputs(
        args.workflow_id,
        f"{output_dir}/{args.workflow_id}",
        cromwell_url
    )
