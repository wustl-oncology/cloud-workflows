import json
import logging
import os
import requests
import subprocess

from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path


# Improvements:
# - optionally determine cost of VM this script runs in. Used for GMS
# - costs from a google-provided csv

TASK_KEY = "jes"
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
    return ("callCaching" in call and call["callCaching"]["hit"])


def from_iso(datetime_str):
    return datetime.fromisoformat(datetime_str.rstrip('Z'))


def cost_machine_type(machine_type, duration_seconds, preemptible = False):
    """
    Calculate the per-minute cost of a machine type.

    Pricing is explained in detail at this page: https://cloud.google.com/compute/vm-instance-pricing
    Cromwell (at least in Feb2022) defaults to N1 instances for all tasks.
    """
    if machine_type.startswith("custom-"):
        vcpus, memory_mb = [int(x) for x in machine_type.split('-')[1:]]
        memory_gb = memory_mb / 2**10
        price = N1_PREEMPTIBLE_MACHINE_PRICE if preemptible else N1_MACHINE_PRICE
        return {"cpu":    min(60, duration_seconds) * vcpus * price["cpu"] / SECONDS_PER_HOUR,
                "memory": min(60, duration_seconds) * memory_gb * price["memory"] / SECONDS_PER_HOUR}
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


def cost_task(task):
    """
    Calculate the total cost to run this task.

    Returns that total and the values used to calculate it.
    """
    assert is_run_task(task)
    # TODO(john): calculate based on events for more accuracy. We're overestimating right now.
    start_time, end_time = task["start"], task["end"]

    duration = from_iso(end_time) - from_iso(start_time)
    total_seconds = duration.total_seconds()

    machine_type = task["jes"]["machineType"]
    preemptible = task["runtimeAttributes"]["preemptible"]
    disks_used = task["runtimeAttributes"]["disks"]

    machine_cost = cost_machine_type(machine_type, total_seconds, preemptible=preemptible)
    disk_cost = cost_disks(disks_used, total_seconds)
    total_cost = machine_cost["cpu"] + machine_cost["memory"] + disk_cost

    return {
        "durationSeconds": total_seconds,
        "duration": str(duration),
        "startTime": start_time,
        "endTime": end_time,
        "machineType": machine_type,
        "memoryCost": machine_cost["memory"],
        "cpuCost": machine_cost["cpu"],
        "diskCost": disk_cost,
        "disks": disks_used,
        "totalCost": total_cost
    }


def cost_workflow(location, workflow_id):
    """
    Determine the totalcost of a workflow.

    Returns total cost, call costs, and start/end time.
    """
    metadata = read_json(f"{location}/{workflow_id}.json")
    call_costs_by_name = {}
    for call_name, calls in metadata["calls"].items():
        for idx, call in enumerate(calls):
            call_key = call_name if call["shardIndex"] == -1 else f"{call_name}_shard-{idx}"
            if is_run_task(call):
                cost = cost_task(call)
                call_costs_by_name[call_key] = cost
            elif is_cached_task(call):
                logging.info(f"Skipping CACHED {call_name}")
            elif is_subworkflow(call):
                cost = cost_workflow(location, call["subWorkflowId"])
                call_costs_by_name[call_key] = cost
            else:
                logging.warning(f"Not a vm, cacheHit, or subworkflow. Failed before VM start? {call_name} {idx}")
    duration = from_iso(metadata["end"]) - from_iso(metadata["start"])
    return {
        "callCosts": call_costs_by_name,
        "totalCost": sum(call["totalCost"] for call in call_costs_by_name.values()),
        "startTime": metadata["start"],
        "endTime": metadata["end"],
        "duration": str(duration),
        "durationSeconds": duration.total_seconds()
    }


if __name__ == "__main__":
    parser = ArgumentParser(description="Generate JSON of billing information for workflow, using local metadata files.")
    parser.add_argument("workflow_id")
    parser.add_argument("metadata_dir")
    args = parser.parse_args()

    log_level = os.environ.get("LOGLEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format='[%(levelname)s] %(message)s'
    )

    cost = cost_workflow(args.metadata_dir.rstrip('/'), args.workflow_id)
    print(json.dumps(cost, indent=4))
