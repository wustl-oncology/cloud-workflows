import json
import logging
import os
import re
import requests
import subprocess
import sys

from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

from costs_json_to_csv import task_costs, write_csv


# Improvements:
# - optionally determine cost of VM this script runs in. Used for GMS
# - costs from a google-provided csv

TASK_KEY = "jes"
CACHED_KEY = "callCaching"
SUBWORKFLOW_KEY = "subWorkflowId"

SECONDS_PER_HOUR = 60 * 60
SECONDS_PER_MONTH = 30 * 24 * SECONDS_PER_HOUR

# Compute VM prices are priced per hour used.
# Charges are done once per second, with a minimum of one minute
# https://cloud.google.com/compute/vm-instance-pricing#billingmodel
# Values taken February 21, 2022. Values change constantly.
# TODO(john) pull price values from a real data source
N1_PREEMPTIBLE_MACHINE_PRICE = {
    "memory": 0.00094, "cpu": 0.00698
}
N1_MACHINE_PRICE = {
    "memory": 0.004446, "cpu": 0.033174
}

# Disks are priced per month used, in granularity of seconds
#    https://cloud.google.com/compute/disks-image-pricing
# Values taken February 21, 2022. Values change constantly.
# TODO(john) pull price values from a real data source
DISK_PRICE = { "SSD": 0.170, "HDD": 0.040 }


# GOOGLE_URL = "http://metadata.google.internal/computeMetadata/v1/instance/attributes"
# requests.get(GOOGLE_URL, headers={'Metadata-Flavor': 'Google'})


def read_json(filename):
    """
    read+parse a JSON file into memory. Works for local and gs:// files
    """
    logging.debug(f"Reading JSON {filename}")
    if filename.startswith("gs://"):
        tmpdir = os.environ.get("TMPDIR", "/tmp")
        tmpfile = f"{Path(tmpdir)}/{Path(filename).name}"
        subprocess.call(['gsutil', '-q', 'cp', '-n', filename, tmpfile])
        with open(tmpfile) as f:
            return json.load(f)
    else:
        with open(filename) as f:
            return json.load(f)


def is_subworkflow(call):
    return SUBWORKFLOW_KEY in call


def is_run_task(call):
    return TASK_KEY in call


def is_cached_task(call):
    return CACHED_KEY in call


def from_iso(datetime_str):
    return datetime.fromisoformat(datetime_str.rstrip('Z'))


def cost_machine_type(machine_type, duration_seconds, preemptible = False):
    """
    Calculate the per-minute cost of a machine type.

    Pricing is explained in detail at this page:
    https://cloud.google.com/compute/vm-instance-pricing

    Cromwell (at least in Feb2022) defaults to N1 instances for all tasks.
    """
    if machine_type.startswith("custom-"):
        vcpus, memory_mb = [int(x) for x in machine_type.split('-')[1:]]
        memory_gb = memory_mb / 2**10
        price = N1_PREEMPTIBLE_MACHINE_PRICE if preemptible else N1_MACHINE_PRICE
        return {"cpu":    max(60, duration_seconds) * vcpus * price["cpu"] / SECONDS_PER_HOUR,
                "memory": max(60, duration_seconds) * memory_gb * price["memory"] / SECONDS_PER_HOUR}
    else:
        raise NotImplementedError(f"Don't know how to handle machine type {machine_type}")


def cost_disks(disks, duration_seconds):
    """
    Calculate the per-minute cost of disks used by the VM.

    Pricing is explained in detail at this page:
    https://cloud.google.com/compute/disks-image-pricing#disk
    """
    if len(disks.split(" ")) != 3:
        raise NotImplementedError(f"Not handling multiple disks yet. {disks}")

    total_gb, disk_type = disks.split(" ")[1:]

    if disk_type not in DISK_PRICE:
        raise NotImplementedError(f"Don't know what to do with disk type {disk_type} for disks: {disks}")
    else:
        return duration_seconds * int(total_gb) * DISK_PRICE[disk_type] / SECONDS_PER_MONTH


def machine_duration(task):
    events = task["executionEvents"]
    bStatus = task["backendStatus"]
    eStatus = task["executionStatus"]

    def find_description(desc):
        return next(event for event in events if event["description"] == desc)

    if bStatus == "Success" and eStatus == "Done":
        def is_start(desc):
            return desc.startswith("Worker ") and desc.endswith("machine")
        start_event = next(event for event in events if is_start(event["description"]))
        end_event = find_description("Worker released")
    else:
        start_event = find_description("RunningJob")
        end_event = find_description("UpdatingJobStore")

    if not (start_event and end_event):
        raise NotImplementedError(f"machine duration couldn't be determined for task. Had backendStatus {bStatus} executionStatus {eStatus} and events {events}")

    return start_event["startTime"], end_event["endTime"]


def cost_task(task):
    """
    Calculate the total cost to run this task.

    Returns that total and the values used to calculate it.
    """
    assert is_run_task(task)
    start_time, end_time = machine_duration(task)

    duration = from_iso(end_time) - from_iso(start_time)
    total_seconds = duration.total_seconds()

    machine_type = task["jes"]["machineType"]
    preemptible = task["preemptible"]
    disks_used = task["runtimeAttributes"]["disks"]

    machine_cost = cost_machine_type(machine_type, total_seconds, preemptible=preemptible)
    disk_cost = cost_disks(disks_used, total_seconds)
    total_cost = machine_cost["cpu"] + machine_cost["memory"] + disk_cost

    return {
        "durationSeconds": total_seconds,
        "duration": str(duration),
        "startTime": task["start"],
        "endTime": task["end"],
        "machineStartTime": start_time,
        "machineEndTime": end_time,
        "machineType": machine_type,
        "memoryCost": machine_cost["memory"],
        "cpuCost": machine_cost["cpu"],
        "diskCost": disk_cost,
        "disks": disks_used,
        "totalCost": total_cost,
        "attempt": task["attempt"],
        "preemptible": preemptible,
        "backendStatus": task["backendStatus"]
    }


def parse_cache_result(call):
    # example: "Cache Hit: 7f84432e-c1e2-42d6-b3ba-c48521c2db47:immuno.extractAlleles:-1"
    # "Cache Hit: (uuid):(callName):(shardIndex)"
    result = call["callCaching"]["result"]
    match = re.match(
        "^Cache Hit: ([-0-9a-f]+):(.+):(-1|[0-9]+)$",
        result
    )
    # These don't do anything to handle the error -- just let the script fail naturally
    if not match:
        logging.error(f"No matches to parse a subworkflow ID out of result {result}")
    if not len(match.groups()) == 3:
        logging.error(f"Match did not result in three groups as expected: len({match.groups()}) == {len(match.groups())}")
    cached_call, call_name, shard_index = match.groups()

    return cached_call, call_name, int(shard_index)


def cost_cached_call(location, call, metadata):
    cached_call, call_name, shard_index = parse_cache_result(call)
    metadata = read_json(f"{location}/{cached_call}.json")
    call_data = next(x for x in metadata["calls"][call_name] if x["shardIndex"] == shard_index)
    return cost_task(call_data)


def call_key(call_name, call):
    ck = call_name
    if call["shardIndex"] != -1:
        ck += "_shard-" + str(call["shardIndex"])
    if call["attempt"] > 1:
        ck += "_retry" + str(call["attempt"] - 1)
    return ck


def cost_workflow(location, workflow_id):
    """
    Determine the total cost of a workflow.

    Returns total cost, call costs, and start/end time.
    """
    metadata = read_json(f"{location}/{workflow_id}.json")
    call_costs_by_name = {}
    for call_name, calls in metadata["calls"].items():
        for idx, call in enumerate(calls):
            ck = call_key(call_name, call)
            if is_run_task(call):
                call_costs_by_name[ck] = cost_task(call)
            elif is_cached_task(call):
                call_costs_by_name[ck] = cost_cached_call(location, call, metadata)
            elif is_subworkflow(call):
                call_costs_by_name[ck] = cost_workflow(location, call["subWorkflowId"])
            else:
                logging.warning(f"Not a vm, cacheHit, or subworkflow. Failed before VM start? {ck}")
    duration = from_iso(metadata["end"]) - from_iso(metadata["start"])
    def total(key):
        return sum(call[key] for call in call_costs_by_name.values())
    return {
        "callCosts": call_costs_by_name,
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

    cost = cost_workflow(args.metadata_dir.rstrip('/'), args.workflow_id)
    if args.csv:
        write_csv(sys.stdout, task_costs(cost))
    else:
        print(json.dumps(cost, indent=4))
