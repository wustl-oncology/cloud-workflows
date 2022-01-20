# Manual Workflow

This document is meant to detail the use-case of creating a Google
Cloud VM instance, preconfigured with Cromwell, to run workflows using
Google Cloud VM instance workers.

This approach gives you the benefits of running workflows with
Cromwell and the benefits of the cloud, but you'll be missing out on
the provenance that comes with leveraging the GMS. The only records of
what runs have been done exists in a file database on your VM, and in
the irretrievable depths of Google metrics. Take care to upload any
files you plan to keep up to your bucket before deleting the instance.


# Interacting with the Google Cloud CLI for the first time

The Google Cloud CLI (gcloud + gsutil) require first-time setup,
[detailed here](../docs/gcloud_setup.md).

# Project Setup

First-time set-up has a few complexities. Use the `resources.sh`
helper script to create resources as needed.

To initialize the project and create necessary resources

    bash resources.sh init-project --project $PROJECT --bucket $GCS_BUCKET

To enable a non-administrator user to run workflows

    bash resources.sh grant-permissions --project $PROJECT --bucket $GCS_BUCKET --email $USER_EMAIL

To revoke these permissions from a

    bash resources.sh revoke-permissions --project $PROJECT --bucket $GCS_BUCKET --email $USER_EMAIL

# Workflow Preparation

Assuming you have a WDL workflow that works in the cloud, the only
preparation you have to do is make sure your data files exist on a GCS
bucket. If you had to create one in [Project
Setup](./README.md#project-setup) then you'll have to upload your
files and create an inputs file with those new paths.

If you already have a compute1 workflow you'd like to run in the
cloud, use `../scripts/cloudize-workflow.py` to ease the process.

Jump into a docker container with the script available
```sh
bsub -Is -q general-interactive -G $GROUP -a "docker(jackmaruska/cloudize-workflow:latest)" /bin/bash
```

Execute the script
```sh
python3 /opt/scripts/cloudize-workflow.py $GCS_BUCKET $WORKFLOW_DEFINITION $LOCAL_INPUT --output=$CLOUD_INPUT
```

Each $VAR should be either set or replaced with your value, e.g.
```sh
export GCS_BUCKET=your-bucket-name
export WORKFLOW_DEFINITION=/path/to/workflow.wdl
export LOCAL_INPUT=/path/to/input.yaml
export CLOUD_INPUT=$PWD/input_cloud.yaml
python3 /opt/scripts/cloudize-workflow.py $GCS_BUCKET $WORKFLOW_DEFINITION $LOCAL_INPUT --output=$CLOUD_INPUT
```
or
```sh
python3 /opt/scripts/cloudize-workflow.py \
    griffith-lab-cromwell \
    /path/to/workflow.wdl \
    /path/to/input.yaml \
    --output=$PWD/input_cloud.yaml
```

# Create the VM

This repo contains a shell wrapper for this command. You should only
need to run this command.

    bash start.sh INSTANCE-NAME --server-account SERVER_ACCOUNT

If you want to modify the settings of the VM in any way, either modify
that script or execute its `gcloud` call manually with whatever
changes you need.

When you're done with the instance, remember to delete it so you don't
burn resources.

    gcloud compute instances delete INSTANCE-NAME


# SSH in to VM

    gcloud compute ssh INSTANCE-NAME

The only reasons I've seen this fail are
1. account authorization, you aren't logged in to an account with
   access to the instance
1. network configuration, the network or subnet in GCP (probably
   default) aren't allowing SSH through the firewall
1. the instance isn't up. It can take a moment for the machine to spin
   up, so try again in a minute or watch the web console to see when
   the instance is ready.

There's no need by default to fuss with SSH keys, your gcloud auth
command should be enough unless configuration has been changed.

Once you're in the VM, wait until the startup script completes with

    journalctl -u google-startup-scripts -f

These logs will stop with a message roughly reading

> google_metadata_script_runner[489]: Finished running startup scripts.
> systemd[1]: google-startup-scripts.service: Succeeded.
> systemd[1]: Finished Google Compute Engine Startup Scripts.
> systemd[1]: google-startup-scripts.service: Consumed 2min 28.421s CPU time.

Then wait until the Cromwell service has started with

    journalctl -u cromwell -f

The Cromwell service will be ready for workflow submissions after a
message roughly reading

> java[13936]: 2022-01-19 21:55:27,357 cromwell-system-akka.dispatchers.engine-dispatcher-7 INFO  - Cromwell 71 service started on 0:0:0:0:0:0:0:0:8000...


When this message is printed, the service is ready to use. If errors
are printed in either log, those will need to be addressed.


# Localize Your Inputs File

You can do this a few ways. In my opinion, the easiest two options
are:

1. Copy-paste contents into your favorite terminal text editor (nano,
   emacs, vim installed by default. Others available via `sudo
   apt-get`).
1. Upload it to your GCS bucket, download into the VM

> On compute1: `gsutil cp /local/path/to.yaml gs://BUCKET/path/to.yaml`
> On cloud VM: `gsutil cp gs://BUCKET/path/to.yaml /local/path/to.yaml`

There's no need to download any of your data from GCS to the
VM. Cromwell will handle providing those files to the worker instances
it creates. All you need is your inputs file and the analysis-wdls
repo located at `/shared/analysis-wdls`. Workflow definitions are
located at `/shared/analysis-wdls/definitions/` and a zipfile of the
dependencies at `/shared/analysis-wdls/workflows.zip`.


## Run a Workflow

Example call for Somatic Exome pipeline with example data

    source /shared/helpers.sh
    submit_workflow /shared/analysis-wdls/definitions/somatic_exome.wdl /shared/analysis-wdls/example-data/somatic_exome.yaml


# Save Timing Diagram and Outputs List

After a workflow is run, before exiting and deleting your VM, make
sure that the timing diagram and the list of outputs are available so
you can make use of the data outside of the cloud.

    source /shared/helpers.sh
    save_artifacts WORKFLOW_ID gs://BUCKET/desired/path

This command will upload the workflow's artifacts to GCS so they can
be used after the VM is deleted. They can be found at paths

    gs://BUCKET/desired/path/WORKFLOW_ID/timing.html
    gs://BUCKET/desired/path/WORKFLOW_ID/outputs.json

The file `outputs.json` will simply be a map of output names to their
GCS locations. The `pull_outputs.py` script can be used to retrieve
the actual files.


# Additional Tools in VM

The instance should start with any tools built into the base operating
system (default ubuntu), packages necessary to operate
(e.g. default-jdk, python3-pip), and packages for convenience
(e.g. curl, less). For a complete list look for `PACKAGES` in
server_startup.py. Anything you'd like to add can be added one-off
with `sudo apt-get` or on subsequent instances by modifying the value
of `PACKAGES` in the startup script.


## Viewing Logs

This is easiest done via `journalctl`.

For startup script logs, use service `google-startup-scripts`, e.g.

    journalctl -u google-startup-scripts

For cromwell logs, use service `cromwell`, e.g.

    journalctl -u cromwell

For additional settings see `journalctl --help`


# Pulling the Outputs from GCS back to the Cluster

After the work in your compute instance is all done, including
`save_artifacts`, and you want to bring your results back to the
cluster, leverage the `pull_outputs.py` script with the generated
`outputs.json` to retrieve the files.

On compute1 cluster, jump into a docker container with the script available
```sh
bsub -Is -q general-interactive -G $GROUP -a "docker(jackmaruska/cloudize-workflow:latest)" /bin/bash
```

Execute the script
```sh
python3 /opt/scripts/pull_outputs.py
    --outputs-file=gs://BUCKET/desired/path/WORKFLOW_ID/outputs.json \
    --outputs-dir=/path/to/outputs/dir
```
