# built-in
import json
import logging
import os
import subprocess
from argparse import ArgumentParser
from pathlib import Path


DEFAULT_OUTPUTS_DIR = './outputs'
DEFAULT_DRYRUN = False

DRYRUN = DEFAULT_DRYRUN

# Update this function to handel both local and GCS paths
# old function
#def download_from_gcs(src, dest):
    #"Copy a GCS file at path `src` to local path `dest`, creating that path if needed."
    #os.makedirs(Path(dest).parent, exist_ok=True)
    #if not Path(dest).is_file():
        #logging.info(f"Downloading {src} to {dest}")
        #if not DRYRUN:
            #subprocess.call(['gsutil', '-q', 'cp', '-n', src, dest])
    #else:
        #logging.info(f"File already exists, skipping download {src} to {dest}")
# new function
def download_file(src, dest):
    """
    Copy a file from `src` to `dest`. 
    - If `src` starts with "gs://", it uses `gsutil` to copy the file from Google Cloud Storage.
    - If `src` is a local path, it uses the `cp` command to copy the file locally.
    """
    os.makedirs(Path(dest).parent, exist_ok=True)  # Ensure the destination directory exists
    if not Path(dest).is_file():  # Check if the file already exists
        logging.info(f"Copying {src} to {dest}")
        if not DRYRUN:
            if src.startswith("gs://"):
                # Use gsutil for Google Cloud Storage paths
                subprocess.call(['gsutil', '-q', 'cp', '-n', src, dest])
            else:
                # Use cp for local paths
                subprocess.call(['cp', src, dest])
    else:
        logging.info(f"File already exists, skipping copy {src} to {dest}")

# old function
#def download(path, value, subdir = None):
#    """
#    Recursively download all output files.
#    GCS file `value` will be downloaded under `path
#    `subdir` is an optional value _only_ for types which need a directory, e.g. lists + dicts
#    If `subdir` is specified, list/dict types will download under `path/subdir`
#    """
#    if isinstance(value, list):
#        for loc in value:
#            download(f"{Path(path)}/{subdir or ''}", loc)
#    elif isinstance(value, dict):
#        for k, v in value.items():
#            download(f"{path}/{subdir or ''}", v, subdir=k)
#    elif isinstance(value, str):
#        if not value.startswith("gs://"):
#            logging.warning(f"Likely not a File output. had a non-GCS path value of {value}")
#        else:
#            download_from_gcs(value, Path(f"{path}/{Path(value).name}"))
#    elif value is None:
#        logging.info(f"Skipping optional output that wasn't defined{': ' + subdir if subdir else ''}")
#    else:
#        logging.error(f"Don't know how to download type {type(value)}. Full object: {value}")

# new function: 
def download(path, value, subdir=None):
    """
    Recursively download all output files.
    - If `value` is a GCS file (starts with "gs://"), it will be downloaded using `download_file`.
    - If `value` is a local file, it will also be handled by `download_file`.
    - `subdir` is an optional value _only_ for types which need a directory, e.g., lists and dicts.
    If `subdir` is specified, list/dict types will download under `path/subdir`.
    """
    if isinstance(value, list):
        for loc in value:
            download(f"{Path(path)}/{subdir or ''}", loc)
    elif isinstance(value, dict):
        for k, v in value.items():
            download(f"{path}/{subdir or ''}", v, subdir=k)
    elif isinstance(value, str):
        # Handle both GCS and local paths
        download_file(value, Path(f"{path}/{Path(value).name}"))
    elif value is None:
        logging.info(f"Skipping optional output that wasn't defined{': ' + subdir if subdir else ''}")
    else:
        logging.error(f"Don't know how to download type {type(value)}. Full object: {value}")


def download_outputs(response, outputs_dir):
    "Download outputs, using their output_name and file extension, not path structure."
    for k, v in response['outputs'].items():
        output_name = k.split(".")[-1]
        download(outputs_dir, v, subdir=output_name)


def read_json(filename):
    """
    read+parse a JSON file into memory. Works for local and gs:// files
    """
    logging.debug(f"Reading JSON {filename}")
    if filename.startswith("gs://"):
        tmpdir = os.environ.get("TMPDIR", "/tmp")
        tmpfile = f"{Path(tmpdir)}/{Path(filename).name}"
        #download_from_gcs(filename, tmpfile)
        download_file(filename, tmpfile)
        with open(tmpfile) as f:
            return json.load(f)
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

    # outputs_file="/storage1/fs1/mgriffit/Active/griffithlab/gc2596/j.yao/immuno_local_copy_output/test_files/pvacseq_test/test_persist_artifacts/workflow_artifacts/outputs.json"
    # outputs_dir="/storage1/fs1/mgriffit/Active/griffithlab/gc2596/j.yao/immuno_local_copy_output/test_files/pvacseq_test/test_pull_outputs"
    DRYRUN = args.dryrun
    outputs_dir = args.outputs_dir

    log_level = os.environ.get("LOGLEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format='[%(levelname)s] %(message)s'
    )

    # download_outputs(read_json(outputs_file), outputs_dir)
    download_outputs(read_json(args.outputs_file), outputs_dir)
