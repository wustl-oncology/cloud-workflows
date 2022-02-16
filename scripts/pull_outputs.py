# built-in
import json
import logging
import os
from argparse import ArgumentParser
from pathlib import Path
from subprocess import Popen, PIPE


DEFAULT_OUTPUTS_DIR = './outputs'
DEFAULT_DRYRUN = False

DRYRUN = DEFAULT_DRYRUN

# --- File system

def ensure_parent_dir_exists(filename):
    os.makedirs(filename.parent, exist_ok=True)


def filename(path):
    """ Return just the name of the file, not including parent directories."""
    return path.split("/")[-1]


# --- Google Cloud Storage

def download_from_gcs(src, dest):
    ensure_parent_dir_exists(dest)
    if not Path(dest).is_file():
        logging.info(f"Downloading {src} to {dest}")
        if not DRYRUN:
            os.system(f"gsutil -q cp -n {src} {dest}")
    else:
        logging.info(f"File already exists, skipping download {src} to {dest}")


# --- Non-general stuff.

def download(path, value):
    if isinstance(value, list):
        for loc in value:
            download(path, loc)
    elif isinstance(value, dict):
        for k, v in value.items():
            download(f"{path}/{k}", v)
    elif isinstance(value, str):
        if not value.startswith("gs://"):
            logging.warning(f"Likely not a File output. had a non-GCS path value of {value}")
        else:
            download_from_gcs(path, Path(f"{path}/{filename(value)}"))
    else:
        logging.error(f"Don't know how to download type {type(value)}. Full object: {value}")


def download_outputs(response, outputs_dir):
    "Download outputs, using their output_name and file extension, not path structure."
    for k, v in response['outputs'].items():
        output_name = k.split(".")[-1]
        download(f"{outputs_dir}/{output_name}", v)


def read_json(filename):
    with open(filename) as f:
        return json.load(f)


if __name__ == "__main__":
    parser = ArgumentParser(description="Download Cromwell outputs for a given workflow.")
    parser.add_argument("--outputs-file",
                        help="JSON file of workflow outputs to pull. Exclusive with workflow_id.")
    parser.add_argument("--outputs-dir",
                        help=f"directory path to download outputs to. Defaults to {DEFAULT_OUTPUTS_DIR}")
    parser.add_argument("--dryrun",
                        help=f"If this arg is set to True, skips the actual download and just prints progress info. Useful for troubleshooting the script. Defaults to {DEFAULT_DRYRUN}")
    args = parser.parse_args()

    DRYRUN = args.dryrun or DEFAULT_DRYRUN

    outputs_dir = args.outputs_dir or DEFAULT_OUTPUTS_DIR

    log_level = os.environ.get("LOGLEVEL", "WARNING").upper()
    logging.basicConfig(
        level=log_level,
        format='[%(levelname)s] %(message)s'
    )

    if args.outputs_file:
        outputs = read_json(args.outputs_file)
    else:  # not (workflow_id or outputs_file):
        raise Exception("must specify either --workflow-id or --outputs-file")

    download_outputs(outputs, outputs_dir)
