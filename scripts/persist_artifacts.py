import json
import logging
import os
import re
import requests

from argparse import ArgumentParser
from pathlib import Path

CROMWELL_API = "http://localhost:8000/api"
LOCAL_DIR=os.environ["HOME"] + "/artifacts"


def _request_workflow(endpoint):
    logging.debug(f"Requesting workflow endpoint {endpoint}")
    return requests.get(f"{CROMWELL_API}/workflows/v1/{endpoint}")


def _save_locally(contents, filename):
    target = f"{LOCAL_DIR}/{filename}"
    logging.debug(f"Writing {target}")
    os.makedirs(Path(target).parent, exist_ok=True)
    with open(target, 'w') as f:
        f.write(contents)


def persist_artifacts_to_gcs(gcs_artifacts_dir):
    logging.info(f"Copying {LOCAL_DIR} to {gcs_artifacts_dir}")
    if logging.root.isEnabledFor(logging.DEBUG):
        os.system(f"gsutil -m cp -r -n {LOCAL_DIR} {gcs_artifacts_dir}")
    else:
        os.system(f"gsutil -q -m cp -r -n {LOCAL_DIR} {gcs_artifacts_dir}")


def json_str(obj):
    return json.dumps(obj, indent=4)


# TODO(john): save info about current VM

def is_cache_hit(call):
    return call.get("callCaching", {}).get("hit", False)


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


def all_calls(metadata):
    """All of a workflow's direct calls, flattened out of the nested structure."""
    for call_name, calls in metadata.get("calls", {}).items():
        for call in calls:
            yield call, call_name


def fetch_resource(resource_type, workflow_id, extension):
    local_path = Path(f"{LOCAL_DIR}/{resource_type}/{workflow_id}.{extension}")
    if local_path.is_file():
        return local_path.read_text()

    logging.debug(f"Fetching {resource_type} for workflow {workflow_id}")
    response = _request_workflow(f"{workflow_id}/{resource_type}")
    if response.ok:
        return response.text
    else:
        logging.error(f"{workflow_id}/{resource_type} returned non-OK response {response}")
        return None


def fetch_metadata(workflow_id):
    """Retrieve metadata object for workflow_id, either local file or as request. """
    result = fetch_resource("metadata", workflow_id, "json")
    if result:
        return json.loads(result)


def fetch_timing(workflow_id):
    return fetch_resource("timing", workflow_id, "html")


def explore(frontier, func):
    explored = []
    while frontier:
        node = frontier.pop()
        if node in explored:
            continue
        explored.append(node)
        discovered = func(node)
        frontier.extend(discovered)


def persist_workflow(call):
    """Locally write all artifacts of a workflow, returning a list of its subworkflows and cached calls."""
    workflow_id, workflow_name = call

    timing = fetch_timing(workflow_id)
    if timing:
        _save_locally(timing, f"timing/{workflow_id}.html")

    metadata = fetch_metadata(workflow_id)
    if not metadata:
        return []
    _save_locally(json_str(metadata), f"metadata/{workflow_id}.json")

    subworkflows = [(call["subWorkflowId"], name)
                    for call, name, _ in all_calls(metadata)
                    if "subWorkflowId" in call]
    cached_calls = [(cached_id(call), name)
                    for call, name, _ in all_calls(metadata)
                    if is_cache_hit(call)]
    return subworkflows + cached_calls


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

    explore([(args.workflow_id, "root")], persist_workflow)

    root_outputs  = {"outputs": fetch_metadata(args.workflow_id)["outputs"]}
    _save_locally(json_str(root_outputs), 'outputs.json')

    os.system(f"cp {LOCAL_DIR}/metadata/{args.workflow_id}.json {LOCAL_DIR}/metadata.json")
    os.system(f"cp {LOCAL_DIR}/timing/{args.workflow_id}.html {LOCAL_DIR}/timing.html")

    persist_artifacts_to_gcs(args.gcs_dir)
