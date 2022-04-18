Resources are prepared to enable running workflows on the cloud either
doing manual interaction with Cromwell, or leveraging GMS to automate
interactions through its familiar interface.


# Motivation

Switching workflow runs to the cloud are primarily motivated by issues
of reliability with the local cluster. Secondary motivations are
numerous, ranging from scalability to data-sharing.


# When to Use

We're starting with a few known use cases that we believe would
benefit from switching to the cloud.

The two use cases we're aiming at first are
1) ad-hoc workflow kickoff through manual intervention
2) workflows kicked off through the GMS


## Manual Kickoff

For people who want to fiddle with workflows, or otherwise dive into
the gears of Cromwell without the burden of the extra GMS
abstractions, this is the approach.

For more information on manual interactions, see
[manual-workflows/README.md](manual-workflows/README.md)


## GMS Kickoff

Our primary focus is GMS integration. The goal is to abstract away as
much of the cloud as we can, and besides the first-time setup
(enabling APIs, creating static resources), ideally make all
interactions done identically to current GMS usage.

For more information on GMS interaction, see
[gms/README.md](gms/README.md)


## Some Other Solution

Every solution has things it's good at and things it's not. Again, the
primary focus here is GMS integration. If you're in a situation that
requires high scalability, mostly meaning highly parallelized
workflows, and you don't have need for the benefits that GMS provides,
what we have here is probably not your best option.

The Bolton Lab was in a similar situation and this solution
consistently ran into reliability issues due to the highly
parallelized nature of the workflow. They ended up using Terra
with more success, so if you're in that situation I would recommend
following their lead.


# Shared Helper Scripts

The README for each section includes instructions that go over
relevant helper scripts for that section. If you'd like to inspect the
helper scripts on their own, the best starting point is
[scripts/README.md](scripts/README.md)


# Docker Image

These scripts are contained within a Docker container image, to they
can be used asynchronously with bsub. This container image can be
found on dockerhub at `mgibio/cloudize-workflow`. Using latest is
always suggested but semantic versioning will be followed in case
prior behavior is needed.

After modifying any scripts, build and tag the docker image

    sh infra.sh build-and-tag VERSION

This command will create docker images with tags `VERSION` and `latest`

# End to End Tutorials

Several attempts to demonstrate running our WDL workflows on Google
Cloud have been created. For example:

- Running the Immunogenomics workflow (immuno.wdl) manually and 
assuming that your input data is stored on the compute1/storage1 
system at WASHU: [immuno-compute1](https://github.com/griffithlab/immuno_gcp_wdl_compute1)  
- Running the Immunogenomics workflow (immuno.wdl) manually and
assuming the your input data is on a local machine that is not 
associated with WASHU in any way. For example, an external institution
or on a personal laptop and Google Cloud account: [immuno-local](https://github.com/griffithlab/immuno_gcp_wdl_local) 

