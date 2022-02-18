import json
import logging
import os
import requests

from argparse import ArgumentParser


CROMWELL_API = "http://localhost:8000/api"


def _save_locally(contents, filename):
    with open(filename, "w") as f:
        json.dump(contents, f)


def _save_gcs(src, dest):
    logging.info(f"Saving {src} to {dest}")
    os.system(f"gsutil -q cp {src} {dest}")


def _request_workflow(endpoint):
    return requests.get(f"{CROMWELL_API}/workflows/v1/{endpoint}")


def _persist_endpoint(endpoint, gcs_dir, filename):
    response = _request_workflow(endpoint)
    if response.ok:
        _save_locally(response.text, filename)
        _save_gcs(filename, f"{gcs_dir}/{filename}")
    else:
        logging.error(f"{endpoint} returned non-OK response {response}")


def save_timing(workflow_id, gcs_dir):
    _persist_endpoint(f"{workflow_id}/timing", gcs_dir, "timing.html")


def save_outputs(workflow_id, gcs_dir):
    _persist_endpoint(f"{workflow_id}/outputs", gcs_dir, "outputs.html")


def save_metadata(workflow_id, gcs_dir):
    """
    Save `metadata` for workflow_id and its subworkflows to `gcs_dir`
    """
    response = _request_workflow(f"{workflow_id}/metadata")
    if response.ok:
        _save_locally(response.text, f"{workflow_id}.json")
        _save_gcs(f"{workflow_id}.json", f"{gcs_dir}/{workflow_id}.json")
        metadata = response.json()
        for k, calls in metadata.get("calls", {}).items():
            for call in calls:
                if "subWorkflowId" in call:
                    save_metadata(call["subWorkflowId"], gcs_dir)
    else:
        logging.error(f"{workflow_id}/metadata endpoint returned non-OK response {response}")


if __name__ == "__main__":
    parser = ArgumentParser(description="Upload Cromwell endpoint responses for a given workflow. Uploads timing, outputs, and metadata (including subworkflow metadata).")
    parser.add_argument("gcs_dir", required=True)
    parser.add_argument("workflow_id", required=True)
    args = parser.parse_args()

    log_level = os.environ.get("LOGLEVEL", "WARNING").upper()
    logging.basicConfig(
        level=log_level,
        format='[%(levelname)s] %(message)s'
    )

    save_timing(args.workflow_id, args.gcs_dir)
    save_outputs(args.workflow_id, args.gcs_dir)
    save_metadata(args.workflow_id, f"{args.gcs_dir}/metadata")
