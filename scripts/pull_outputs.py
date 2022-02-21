# built-in
import json
import logging
import os
from argparse import ArgumentParser
from pathlib import Path
from subprocess import Popen, PIPE

from google.cloud import storage


DEFAULT_OUTPUTS_DIR = './outputs'
DEFAULT_DRYRUN = False

DRYRUN = DEFAULT_DRYRUN


def download_from_gcs(src, dest):
    "Copy a GCS file at path `src` to local path `dest`, creating that path if needed."
    os.makedirs(Path(dest).parent, exist_ok=True)
    ensure_parent_dir_exists(dest)
    if not Path(dest).is_file():
        logging.info(f"Downloading {src} to {dest}")
        if not DRYRUN:
            os.system(f"gsutil -q cp -n {src} {dest}")
    else:
        logging.info(f"File already exists, skipping download {src} to {dest}")


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
            download_from_gcs(path, Path(f"{path}/{Path(value).name}"))
    else:
        logging.error(f"Don't know how to download type {type(value)}. Full object: {value}")


def download_outputs(response, outputs_dir):
    "Download outputs, using their output_name and file extension, not path structure."
    for k, v in response['outputs'].items():
        output_name = k.split(".")[-1]
        download(f"{outputs_dir}/{output_name}", v)


def read_json(filename):
    """
    read+parse a JSON file into memory. Works for local and gs:// files
    """
    logging.debug(f"Reading JSON {filename}")
    if filename.startswith("gs://"):
        return json.loads(gcs_blob(filename).download_as_text())
    else:
        with open(filename) as f:
            return json.load(f)


if __name__ == "__main__":
    parser = ArgumentParser(description="Download Cromwell outputs for a given workflow.")
    parser.add_argument("--outputs-file",
                        required=True,
                        help="JSON file of workflow outputs to pull. Exclusive with workflow_id.")
    parser.add_argument("--outputs-dir",
                        default=DEFAULT_OUTPUTS_DIR,
                        help=f"directory path to download outputs to.")
    parser.add_argument("--dryrun",
                        action="store_true",
                        help=f"Skips the actual download and just prints progress info. Useful for troubleshooting the script.")
    args = parser.parse_args()

    DRYRUN = args.dryrun
    outputs_dir = args.outputs_dir

    log_level = os.environ.get("LOGLEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format='[%(levelname)s] %(message)s'
    )

    download_outputs(read_json(args.outputs_file), outputs_dir)
