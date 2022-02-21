Some helper scripts for interacting with the Cromwell server.


# pull\_outputs.py

pull_outputs.py will query a Cromwell server for the outputs
associated with a workflow, and download them. For details on usage,
see `python3 scripts/pull_outputs.py --help`.

Requirements to run this script:
 - able to reach the Cromwell server's endpoints
 - authenticated by Google
 - authorized to read files from specified GCS bucket


# cloudize-workflow.py

cloudize-workflow.py will accept a workflow, its inputs, and a GCS
bucket, and prepare a new inputs file to run that workflow on the
cloud. The script assumes the workflow definition is cloud-ready, the
file parameters in the input file are all available, and you have
access to upload to a GCS bucket. For details on usage, see `python3
scripts/cloudize-workflow.py --help`

Requirements to run this script:
 - access to read all file paths specified in workflow inputs
 - authenticated by Google
 - authorized to write files to specified GCS bucket


# submit\_workflow.sh

This script is the least user-ready script but it's still available
as-needed. It's essentially just composing the steps "zip the workflow
dependencies" and "POST to the server with curl".  Recommendation is
not to use this script directly until a more user-friendly version is
made, but modify or extract from it what is needed to zip workflow
dependencies for your case.

It's current iteration is expected to be used as follows

Given the location of a workflow definition, perform a zip on a
pre-defined location for WDL workflows (ANALYSIS\_WDLS), then curl with
those inputs, the newly generated zip, and a pre-defined
WORKFLOW\_OPTIONS file.


# estimate\_billing.py

This script generates a JSON file which estimates the cost of a
workflow run. Takes both a root workflow_id to estimate, and a path to
a directory with a pile of JSON files named
`<workflow_id>.json`. These are generated with `persist_artifacts.py`
which saves them both locally and in GCS. `estimate_billing.py` works
for either local or GCS paths, but if you want to run multiple times
you should probably get local copies first and run them on that.

Estimation is done by crawling the metadata.json files of the root
workflow, and any of its subworkflows, to find the VM characteristics
for each call. Cost of a task is roughly

    (cost_vm_cpu + cost_vm_ram + cost_disks) * duration

Outputs to stdout in JSON format. You'll want to call with `>
costs.json` or similar. Each workflow has its total cost, start/end
times, duration, and its calls (tasks + workflows) costs. Each task
has its total cost, start/end times, duration, machine type, disks,
and prices.


See the Google docs for pricing information
- VM: https://cloud.google.com/compute/vm-instance-pricing
- disks: https://cloud.google.com/compute/disks-image-pricing#disk
