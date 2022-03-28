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


def _fetch_metadata(workflow_id):
    """Retrieve metadata object for workflow_id, either local file or as request. """
    result = fetch_resource("metadata", workflow_id, "json")
    if result:
        return json.loads(result)


def fetch_timing(workflow_id):
    return fetch_resource("timing", workflow_id, "html")


def fetch_metadata(workflow_id):
    """Fetch metadata for workflow_id and all its subworkflows.

    Uses local files for any available.

    Cromwell API allows doing this in the metadata endoint BUT it
    times out on larger workflows like Immuno, which renders it
    basically useless to us. Crawl it ourselves. This puts everything
    into memory. If that becomes an issue (which would be very
    surprising to me) then it should be modified to a generator of
    key-value pairs.
    """
    metadata_by_workflow_id = {}
    workflow_ids_frontier = [(workflow_id, "root")]
    while workflow_ids_frontier:
        workflow_id, workflow_name = workflow_ids_frontier.pop()

        if workflow_id in metadata_by_workflow_id:
            continue

        metadata = _fetch_metadata(workflow_id)
        if not metadata:
            continue

        metadata_by_workflow_id[workflow_id] = metadata
        # Follow subworkflows
        subworkflows = [(call["subWorkflowId"], name)
                        for call, name, _ in all_calls(metadata)
                        if "subWorkflowId" in call]
        workflow_ids_frontier.extend(subworkflows)
        # Follow cached calls
        cached_calls = [(cached_id(call), name)
                        for call, name, _ in all_calls(metadata)
                        if is_cache_hit(call)]
        workflow_ids_frontier.extend(cached_calls)

    return metadata_by_workflow_id


def fetch_all_timing(metadata_by_workflow_id):
    """ Fetch timing contents for every workflow, storing in memory.

    Skips any which already exist as local files."""
    timing_by_workflow_id = {}
    for workflow_id, metadata in metadata_by_workflow_id.items():
        timing = fetch_timing(workflow_id)
        if timing:
            timing_by_workflow_id[workflow_id] = timing
    return timing_by_workflow_id


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

    metadata_by_workflow_id = fetch_metadata(args.workflow_id)
    timing_by_workflow_id = fetch_all_timing(metadata_by_workflow_id)

    # Save root with special names for easy access
    root_metadata = metadata_by_workflow_id[args.workflow_id]
    _save_locally(json_str(root_metadata), 'metadata.json')

    root_timing = timing_by_workflow_id.get(args.workflow_id, None)
    if root_timing:
        _save_locally(root_timing, 'timing.html')

    root_outputs  = {"outputs": root_metadata["outputs"]}
    _save_locally(json_str(root_outputs), 'outputs.json')

    # Save everything else in dirs. We also save the root workflow
    # info here, duplicating it, just for ease of crawling back to
    # root. If we want to remove that, simply uncomment the following
    # line:
    #
    # del metadata_by_workflow_id[args.workflow_id]
    #
    for workflow_id, metadata in metadata_by_workflow_id.items():
        _save_locally(json_str(metadata), f"metadata/{workflow_id}.json")
    for workflow_id, timing in timing_by_workflow_id.items():
        _save_locally(timing, f"timing/{workflow_id}.html")

    persist_artifacts_to_gcs(args.gcs_dir)
