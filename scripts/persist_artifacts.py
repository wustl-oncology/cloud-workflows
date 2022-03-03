import json
import logging
import os
import re
import requests

from argparse import ArgumentParser


CROMWELL_API = "http://localhost:8000/api"


def _save_locally(contents, filename):
    with open(filename, "w") as f:
        f.write(contents)


def _save_gcs(src, dest):
    os.system(f"gsutil -q cp -n {src} {dest}")


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
    logging.info(f"Saving timing.html for workflow {workflow_id}")
    _persist_endpoint(f"{workflow_id}/timing", gcs_dir, "timing.html")


def save_outputs(workflow_id, gcs_dir):
    logging.info(f"Saving outputs.json for workflow {workflow_id}")
    _persist_endpoint(f"{workflow_id}/outputs", gcs_dir, "outputs.html")


# TODO(john): save info about current VM


def is_cache_hit(call):
    if ("callCaching" in call) and not ("hit" in call["callCaching"]):
        logging.debug(f"callCaching entry with no hit key: {call}")
        return False
    else:
        return ("callCaching" in call) \
            and ("hit" in call["callCaching"]) \
            and call["callCaching"]["hit"]


def cached_id(call):
    """ Extract the ID of the cached version of `call` from `call[callCaching][result]`. """
    # example: "Cache Hit: 7f84432e-c1e2-42d6-b3ba-c48521c2db47:immuno.extractAlleles:-1"
    # "Cache Hit: (uuid):(workflowName):(shardIndex)"
    result = call["callCaching"]["result"]
    match = re.match(
        "Cache Hit: ([-0-9a-f]+):(.+):(-1|[0-9]+)",
        result
    )
    # These don't do anything to handle the error -- just let the script fail naturally
    if not match:
        logging.error(f"No matches to parse a subworkflow ID out of result {result}")
    if not len(match.groups()) == 3:
        logging.error(f"Match did not result in three groups as expected: len({match.groups()}) == {len(match.groups())}")
    cached_call, _workflow_name, _shard_index = match.groups()
    return cached_call


def save_metadata(workflow_id, gcs_dir):
    """ Save `metadata` for workflow_id and its subworkflows to `gcs_dir`. """
    logging.info(f"Saving metadata json for workflow {workflow_id}")
    response = _request_workflow(f"{workflow_id}/metadata")
    if response.ok:
        _save_locally(response.text, f"{workflow_id}.json")
        _save_gcs(f"{workflow_id}.json", f"{gcs_dir}/{workflow_id}.json")
        metadata = response.json()
        for k, calls in metadata.get("calls", {}).items():
            for call in calls:
                if "subWorkflowId" in call:
                    logging.debug(f"Call {k} is a subworkflow with id {call['subWorkflowId']}, save it.")
                    save_metadata(call["subWorkflowId"], gcs_dir)
                elif is_cache_hit(call):
                    cached_call = cached_id(call)
                    logging.debug(f"Call {k} is a cached task with id {cached_call}, save it.")
                    save_metadata(cached_call, gcs_dir)
    else:
        logging.error(f"{workflow_id}/metadata endpoint returned non-OK response {response}")


if __name__ == "__main__":
    parser = ArgumentParser(description="Upload Cromwell endpoint responses for a given workflow. Uploads timing, outputs, and metadata (including subworkflow metadata).")
    parser.add_argument("gcs_dir")
    parser.add_argument("workflow_id")
    args = parser.parse_args()

    log_level = os.environ.get("LOGLEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format='[%(levelname)s] %(message)s'
    )

    save_timing(args.workflow_id, args.gcs_dir)
    save_outputs(args.workflow_id, args.gcs_dir)
    save_metadata(args.workflow_id, f"{args.gcs_dir}/metadata")
