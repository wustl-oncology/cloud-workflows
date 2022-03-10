import json
import csv
import sys

from argparse import ArgumentParser
from pathlib import Path


def task_costs(workflow_cost):
    # iterate through callCosts, nesting until it bottoms out.
    # Depth first, to do least huge duplications first
    # convert innermost object to a line, include name and include path there in some fashion
    call_frontier = list(workflow_cost["callCosts"].items())
    entries = []
    while call_frontier:
        call_name, call_costs = call_frontier.pop()
        if "callCosts" in call_costs:  # call is a workflow, not a task
            call_frontier.extend(call_costs["callCosts"].items())
        else:  # call is a task
            entries.append({"callName": call_name, **call_costs})
    return entries


def write_csv(fp, results_dict):
    if results_dict:
        writer = csv.DictWriter(fp, fieldnames=results_dict[0].keys(), lineterminator='\n')
        writer.writeheader()
        writer.writerows(results_dict)


if __name__ == "__main__":
    parser = ArgumentParser(description="Convert output of estimate_billing.py, a JSON containing billing information for a workflow, into a CSV format.")
    parser.add_argument("input_file")
    args = parser.parse_args()

    costs_json = json.loads(Path(args.input_file).read_text())
    results = task_costs(costs_json)
    write_csv(sys.stdout, results)
