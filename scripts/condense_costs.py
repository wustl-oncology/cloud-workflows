import csv
import re
import sys

from argparse import ArgumentParser
from collections import OrderedDict
from pathlib import Path


# Matches the shard and retry suffixes call_key() (in gb_estimate_billing.py)
# appends to a call name, e.g. "trimFastq_shard-2_retry1" -> "trimFastq"
SUFFIX_RE = re.compile(r"(_shard-\d+|_retry\d+)")

# Output column name -> source column name in the input CSV/TSV
SUMMED_FIELDS = OrderedDict([
    ("total", "totalCost"),
    ("cpu", "cpuCost"),
    ("memory", "memoryCost"),
    ("disk", "diskCost"),
])


def base_task_name(call_name):
    """
    Strips shard/retry suffixes so all shards/attempts of one logical task
    condense into a single row, e.g. "trimFastq_shard-2_retry1" -> "trimFastq"
    """
    return SUFFIX_RE.sub("", call_name)


def condense(rows):
    """
    Sums totalCost/cpuCost/memoryCost/diskCost per base task name.
    Returns an ordered dict of task name -> {total, cpu, memory, disk}
    """
    totals = OrderedDict()
    for row in rows:
        name = base_task_name(row["callName"])
        entry = totals.setdefault(name, {key: 0.0 for key in SUMMED_FIELDS})
        for out_key, src_key in SUMMED_FIELDS.items():
            entry[out_key] += float(row[src_key])
    return totals


def write_report(fp, totals):
    writer = csv.writer(fp, delimiter='\t', lineterminator='\n')
    writer.writerow(["task"] + list(SUMMED_FIELDS.keys()))
    for name, costs in sorted(totals.items(), key=lambda kv: kv[1]["total"], reverse=True):
        writer.writerow([name] + [f"{costs[key]:.6f}" for key in SUMMED_FIELDS])


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Condense a per-task costs CSV/TSV (from costs_json_to_csv.py) into "
                    "per-task-type totals, with shards and retries of the same task merged "
                    "into one row, sorted by total cost descending."
    )
    parser.add_argument("input_file", help="CSV or TSV produced by costs_json_to_csv.py")
    parser.add_argument("--delimiter", default=None,
                         help="Field delimiter of input_file. Defaults to tab for a .tsv "
                              "extension, comma otherwise.")
    args = parser.parse_args()

    delimiter = args.delimiter
    if delimiter is None:
        delimiter = '\t' if Path(args.input_file).suffix == '.tsv' else ','

    with open(args.input_file, newline='') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        totals = condense(reader)

    write_report(sys.stdout, totals)
