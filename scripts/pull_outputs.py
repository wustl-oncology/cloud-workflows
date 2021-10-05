# built-in
import os
import re
import requests
from argparse import ArgumentParser
from pathlib import Path

DEFAULT_CROMWELL_URL = "http://34.69.35.61:8000"
DEFAULT_OUTPUT_DIR = './outputs'

# --- File system

def ensure_parent_dir_exists(filename):
    os.makedirs(filename.parent, exist_ok=True)

def file_extensions(path):
    "Extract all file extensions, e.g. 'foo.bam.bai' will return '.bam.bai'"
    return ".".join(path.split("/")[-1].split(".")[:1])


# --- Google Cloud Storage

def download_from_gcs(src, dest):
    ensure_parent_dir_exists(dest)
    if not Path(dest).is_file():
        os.system(f"gsutil cp {src} {dest}")


# --- Cromwell server
def endpoint(hostname, route):
    return f"{hostname.strip('/')}/{route.strip('/')}"

def request_outputs(workflow_id, cromwell_url):
    """Requests the output file paths for a given workflow_id."""
    url = endpoint(cromwell_url, f'/api/workflows/v1/{workflow_id}/outputs')
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def flatten(x):
    """Raises elements of sublists into the main list."""
    def ensure_list(output):
        if isinstance(output, list):
            return output
        else:
            return [output]
    return [z for y in x for z in ensure_list(y)]

# --- Do the download

def structured_download(response, output_dir):
    "Download outputs, maintaining their filepath structure."
    for src in flatten(response['outputs'].values()):
        download_from_gcs(src, Path(f"{output_dir}/{Path(src).parent.stem}/{Path(src).name}"))


def flat_download(response, output_dir):
    "Download outputs, using their output_name and file extension, not path structure."
    for k, gcs_loc in response['outputs'].items():
        output_name = k.split(".")[-1]
        if isinstance(gcs_loc, list):
            for loc in locs:
                filename = loc.split("/")[-1]
                download_from_gcs(loc, Path(f"{output_dir}/{output_name}/{filename}"))
        else:
            download_from_gcs(gcs_loc, Path(f"{output_dir}/{output_name}.{file_extensions(gcs_loc)}"))


def download_outputs(workflow_id, output_dir, cromwell_url):
    response = request_outputs(workflow_id, cromwell_url)
    structured_download(response, output_dir)


if __name__ == "__main__":
    parser = ArgumentParser(description="Download Cromwell outputs for a given workflow.")
    parser.add_argument("workflow_id", help="the UUID of the workflow run to pull outputs for.")
    parser.add_argument("-o", "--output",
                        help=f"directory path to download outputs to. Defaults to {DEFAULT_OUTPUT_DIR}")
    parser.add_argument("--cromwell-url",
                        help=f"URL of the relevant Cromwell server. Honors env var CROMWELL_URL. Defaults to {DEFAULT_CROMWELL_URL}")
    args = parser.parse_args()

    output_dir = args.output or DEFAULT_OUTPUT_DIR
    cromwell_url = args.cromwell_url or os.environ['CROMWELL_URL'] or DEFAULT_CROMWELL_URL

    download_outputs(
        args.workflow_id,
        f"{output_dir}/{args.workflow_id}",
        cromwell_url
    )
