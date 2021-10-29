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


# Interacting with the CLI for the first time

If google-cloud-sdk isn't installed, start there.


## Installing google-cloud-sdk
On compute1 clients it should already be installed.

To work from a docker container, the image `google/cloud-sdk:latest`
can be used.

To work from a local machine, use your package manager to install
it. For MacOS the command is

    brew install --cask google-cloud-sdk

This package will give you access to the commands `gcloud` and
`gsutil`.


## Configuration

Log in through Google with your WashU account

    gcloud auth login

They'll provide a link which sends you to Google authentication, and
will either automatically log in on verification, or provide a code
for the terminal prompt.

Once you're logged in, set your project and zone. If you don't know
your project name, it can be viewed at
[console.cloud.google.com](console.cloud.google.com) in the top-left
corner, in a dropdown menu of your account's projects.

    gcloud config set project PROJECT-NAME
    gcloud config set zone us-central1-c


# Project Setup

For manual Cromwell workflows only two requirements must be met for
first-time setup:
1. You must have access to a GCS bucket for your data.
1. Your user must have permissions to read/write from the bucket, and
   to create/delete compute VMs.

## Create a GCS bucket

A user with proper permissions can execute this command to create a bucket.

    gsutil mb -b on gs://BUCKET_NAME

Bucket names are globally-unique so it may take a few tries to get a
name that works.


## Grant a new user permissions

Ideally at some point these will be merged into a single permission.

    gsutil iam ch user:EMAIL:objectViewer gs://BUCKET_NAME
    gsutil iam ch user:EMAIL:objectCreator gs://BUCKET_NAME
    gcloud projects add-iam-policy-binding PROJECT_NAME \
        --member=user:EMAIL --role=roles/compute.instanceAdmin


## Remove a user's permissions

Ideally at some point these will be merged into a single permission.

    gsutil iam ch -d user:EMAIL gs://BUCKET_NAME
    gcloud projects remove-iam-policy-binding PROJECT_NAME \
        --member=user:EMAIL --role=roles/compute.instanceAdmin


# Workflow Preparation

Assuming you have a WDL workflow that works in the cloud, the only
preparation you have to do is make sure your data files exist on a GCS
bucket. If you had to create one in [[First-Time Setup]] then you'll
have to upload your files and create an inputs file with those new
paths.

If you already have a compute1 workflow you'd like to run in the
cloud, use [cloudize-workflow.py](../scripts/cloudize-workflow.py) to ease the
process.

For a detailed walkthrough, see [the tutorial](../docs/tutorial.md)
through section 1. Processing Input File.


# Create the VM

This repo contains a shell wrapper for this command. You should only
need to run this command.

    sh ./start INSTANCE-NAME

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


# Localize Your Inputs File

You can do this a few ways. In my opinion, the easiest two options
are:

1. Copy-paste contents into your favorite terminal text editor (nano,
   emacs, vim installed by default. Others available via `sudo
   apt-get`).
1. Upload it to your GCS bucket, download into the VM
   On compute1: gsutil cp /local/path/to.yaml gs://BUCKET/path/to.yaml
   On cloud VM: gsutil cp gs://BUCKET/path/to.yaml /local/path/to.yaml

There's no need to download any of your data from GCS to the
VM. Cromwell will handle providing those files to the worker instances
it creates. All you need is your inputs file and the analysis-wdls
repo located at `/shared/analysis-wdls`. Workflow definitions are
located at `/shared/analysis-wdls/definitions/` and a zipfile of the
dependencies at `/shared/analysis-wdls/workflows.zip`.


# Interact with Cromwell

Once you're in the VM instance, Cromwell commands can be executed as
normal with the following base command

    java -Dconfig.file=/opt/cromwell/config/cromwell.conf -jar /opt/cromwell/jar/cromwell.jar

Any modifications to cromwell.conf can be made in the VM if they're a
one-off, or in this repo to apply for subsequent instances.

TODO: expand to "run a workflow", "run a server", execute helper for
timing diagram


# Additional Tools in VM

The instance should start with any tools built into the base operating
system (default ubuntu), packages necessary to operate
(e.g. default-jdk, python3-pip), and packages for convenience
(e.g. curl, less). For a complete list look for `PACKAGES` in
server_startup.py. Anything you'd like to add can be added one-off
with `sudo apt-get` or on subsequent instances by modifying the value
of `PACKAGES` in the startup script.

There also is a file, `/shared/helpers.sh` containing helpers for the
shell. I mostly use it to remember lengthy commands or file
locations. If there's anything you find useful in that file, `source
/shared/helpers.sh` to use them from the terminal.

TODO: more hand-holding


# Q&A

Q: Why do workflows have to be in WDL?
A: We ran into issues with Cromwell not sizing up disk space on worker
instances. If you want to wrestle with that or if you think your data
won't exceed the default, go for it.
