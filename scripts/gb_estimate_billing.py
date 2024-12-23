import json
import logging
import os
import re
import subprocess
import sys

from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

from costs_json_to_csv import task_costs, write_csv


COMPLETED_TASK_KEY = "executionStatus"
CACHED_KEY = "callCaching"
SUBWORKFLOW_KEY = "subWorkflowId"


SECONDS_PER_HOUR = 60 * 60
SECONDS_PER_MONTH = 30 * 24 * SECONDS_PER_HOUR


# Taken from https://cloud.google.com/compute/vm-instance-pricing#general-purpose_machine_type_family on 11/6/24
# Prices are priced per hour used.
# Charges are done once per second, with a minimum of one minute
n1_machine_price = {
    "memory": 0.004906,
    "cpu": 0.036602
}


# Taken from https://cloud.google.com/spot-vms/pricing#pricing-components on 11/6/24
# Prices are priced per hour used.
# Charges are done once per second, with a minimum of one minute
n1_preemptible_machine_price = {
    "memory": 0.000939,
    "cpu": 0.00702
}


# Taken from https://cloud.google.com/compute/disks-image-pricing#disk on 11/6/24
# Price is charged monthly per GiB used, prorated based on a granularity of seconds
disk_price = {
    "SSD": 0.204,
    "HDD": 0.048
}


def load_metadata(metadata_dir, workflow_id):
    """
    Reads and parses a JSON file into memory. Works for local files and gs:// file paths
    """
    path = f"{metadata_dir}/{workflow_id}.json"
    if path.startswith("gs://"):
        tmpdir = os.environ.get("TMPDIR", "/tmp")
        tmpfile = f"{Path(tmpdir)}/{Path(path).name}"
        subprocess.call(['gsutil', '-q', 'cp', '-n', path, tmpfile])
        with open(tmpfile) as f:
            data = json.load(f)
    else:
        with open(path, 'r') as f:
            data = json.load(f)
    return data


def get_calls(metadata):
    return (metadata.get("calls", {}))


def is_cached_task(call):
    if CACHED_KEY in call:
        return call[CACHED_KEY]["hit"] == True
    return False


def is_subworkflow(call):
    return SUBWORKFLOW_KEY in call


def is_task_completed(call):
    return call[COMPLETED_TASK_KEY] == "Done"


def convert_from_iso(datetime_str):
    return datetime.fromisoformat(datetime_str.rstrip('Z'))


def get_machine_duration(task):
    """
    Returns the start and end time of a specific task
    """
    events = task["executionEvents"]

    def find_description(desc):
        return next(event for event in events if event["description"] == desc)

    start_event = find_description("RunningJob")
    end_event = find_description("UpdatingJobStore")

    if not (start_event and end_event):
        raise NotImplementedError(f"machine duration couldn't be determined for a task. Had events {events}")

    return start_event["startTime"], end_event["endTime"]


def get_machine_cost(task, total_seconds, preemptible):
    """
    Calculate the per-minute cost of running a machine
    Assumes a N1 instance for all tasks
    """
    cpu_amount = int(task["runtimeAttributes"]["cpu"])
    memory_amount = task["runtimeAttributes"]["memory"]

    match = re.search(r"(\d+)", memory_amount)
    memory_value = int(match.group(1))
    memory_amount = memory_value if "GB" in memory_amount else memory_value / 1000
    price = n1_preemptible_machine_price if preemptible else n1_machine_price

    return {"cpu":    max(60, total_seconds) * cpu_amount * price["cpu"] / SECONDS_PER_HOUR,
            "memory": max(60, total_seconds) * memory_amount * price["memory"] / SECONDS_PER_HOUR}


def get_disk_cost(disks_used, total_seconds):
    """
    Returns the total disk cost, can only handle tasks that make use of a single disk
    """
    if len(disks_used.split(" ")) != 3:
        raise NotImplementedError(f"Not handling multiple disks yet. {disks_used}")
    total_gb, disk_type = disks_used.split(" ")[1:]

    if disk_type not in disk_price:
        raise NotImplementedError(f"Don't know what to do with disk type {disk_type} for disks: {disks_used}")
    else:
        return total_seconds * int(total_gb) * disk_price[disk_type] / SECONDS_PER_MONTH


def parse_cache_result(call):
    """
    Parses the cache result field into different subunits
    Example of a result: "Cache Hit: 7f84432e-c1e2-42d6-b3ba-c48521c2db47:immuno.extractAlleles:-1"
    "Cache Hit: (uuid):(callName):(shardIndex)"
    """
    result = call["callCaching"]["result"]
    match = re.match(
        "^Cache Hit: ([-0-9a-f]+):(.+):(-1|[0-9]+)$",
        result
    )
    if not match:
        logging.error(f"No matches to parse a subworkflow ID out of result {result}")
    if not len(match.groups()) == 3:
        logging.error(f"Match did not result in three groups as expected: len({match.groups()}) == {len(match.groups())}")
    cached_call, call_name, shard_index = match.groups()

    return cached_call, call_name, int(shard_index)


def get_cached_cost(metadata_dir, call, metadata):
    """
    Pulls the metadata for the matching cached task and passes it to get_task_cost
    """
    cached_call_id, call_name, shard_index = parse_cache_result(call)
    metadata = load_metadata(metadata_dir, cached_call_id)
    call_data = next(x for x in metadata["calls"][call_name] if x["shardIndex"] == shard_index)
    return get_task_cost(call_data)


def get_task_cost(task):
    """
    Calculates the total cost to run a specific task
    Returns the total and the values used to calculate it
    """
    start_time, end_time = get_machine_duration(task)
    duration = convert_from_iso(end_time) - convert_from_iso(start_time)
    total_seconds = duration.total_seconds()

    preemptible = task["preemptible"]
    disks_used = task["runtimeAttributes"]["disks"]
    machine_cost = get_machine_cost(task, total_seconds, preemptible)
    disk_cost = get_disk_cost(disks_used, total_seconds)
    total_cost = machine_cost["cpu"] + machine_cost["memory"] + disk_cost

    return {
        "durationSeconds": total_seconds,
        "duration": str(duration),
        "startTime": task["start"],
        "endTime": task["end"],
        "machineStartTime": start_time,
        "machineEndTime": end_time,
        "memoryCost": machine_cost["memory"],
        "cpuCost": machine_cost["cpu"],
        "diskCost": disk_cost,
        "disks": disks_used,
        "totalCost": total_cost,
        "attempt": task["attempt"],
        "preemptible": preemptible,
        "backendStatus": task["backendStatus"]
    }


def call_key(call_name, call):
    ck = call_name
    if call["shardIndex"] != -1:
        ck += "_shard-" + str(call["shardIndex"])
    if call["attempt"] > 1:
        ck += "_retry" + str(call["attempt"] - 1)
    return ck


def get_workflow_cost(metadata_dir, workflow_id):
    """
    Calculates the cost of an entire workflow
    Returns total costs, call costs, and start/end time
    """
    metadata = load_metadata(metadata_dir, workflow_id)
    calls = get_calls(metadata)
    call_costs = {}
    for call_name, details in calls.items():
        for _, call in enumerate(details):
            ck = call_key(call_name, call)
            if is_task_completed(call):
                if is_cached_task(call):
                    call_costs[ck] = get_cached_cost(metadata_dir, call, metadata)
                elif is_subworkflow(call):
                    call_costs[ck] = get_workflow_cost(metadata_dir, call[SUBWORKFLOW_KEY])
                else:
                    call_costs[ck] = get_task_cost(call)
            else:
                logging.error(f"{call_name} has not completed running, cost cannot be calculated")
    duration = convert_from_iso(metadata["end"]) - convert_from_iso(metadata["start"])
    def total(key):
        return sum(call[key] for call in call_costs.values())
    return {
        "callCosts": call_costs,
        "totalCost": total("totalCost"),
        "diskCost": total("diskCost"),
        "cpuCost": total("cpuCost"),
        "memoryCost": total("memoryCost"),
        "startTime": metadata["start"],
        "endTime": metadata["end"],
        "duration": str(duration),
        "durationSeconds": "%.3f" % duration.total_seconds(),
        "workflowId": workflow_id
    }


if __name__ == "__main__":
    parser = ArgumentParser(description="Generate JSON of billing information for workflow, using local metadata files.")
    parser.add_argument("workflow_id")
    parser.add_argument("metadata_dir")
    parser.add_argument("--csv", action="store_true", default=False)
    args = parser.parse_args()

    log_level = os.environ.get("LOGLEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format='[%(levelname)s] %(message)s'
    )

    cost = get_workflow_cost(args.metadata_dir.rstrip('/'), args.workflow_id)
    if args.csv:
        write_csv(sys.stdout, task_costs(cost))
    else:
        print(json.dumps(cost, indent=4))