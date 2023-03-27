# Cloud Workflow Orchestration

This repo contains resources designed to enable running genomic analysis workflows on the cloud. This includes documentation and tools for setting up Google Cloud appropriately, spinning up VMs to run the workflow, monitoring runs, and retrieving results.

It is designed to be used in concert with the workflows in the [analysis-wdls repository](https://github.com/wustl-oncology/analysis-wdls), though other WDL workflows should certainly work as well.  

## Quick Start
There are two supported methods of launching workflows documented in the following pages:

1. [manual submission to Cromwell](https://github.com/wustl-oncology/cloud-workflows/blob/main/manual-workflows/README.md), 
2. leveraging WUSTL's [GMS to automate interactions](https://github.com/wustl-oncology/cloud-workflows/tree/main/gms).

There are also several end-to-end demonstrations of running our WDL workflows on Google Cloud:

- Running the Immunogenomics workflow (immuno.wdl) manually and 
assuming that your input data is stored on the compute1/storage1 
system at WASHU: [immuno-compute1](https://github.com/griffithlab/immuno_gcp_wdl_compute1)  

- Running the Immunogenomics workflow (immuno.wdl) manually and
assuming the your input data is on a local machine that is not 
associated with WASHU in any way. For example, an external institution
or on a personal laptop and Google Cloud account: [immuno-local](https://github.com/griffithlab/immuno_gcp_wdl_local) 


## More Information

### Motivation

Using the cloud to run workflows has many advantages, including avoiding reliability or access issues with local clusters, enabling scalability, and easing data-sharing.  

### Limitations

Cromwell does a solid job of orchestrating workflows such as the ones provided in our analysis-wdls repository, and scales well to dozens of samples running dozens of steps at a time. If you're in a situation that requires even higher scalability, to thousands of samples or uses massively parallelized workflows, this backend may not be your best option, and investigating Terra or DNAnexus might be worthwhile. 

### Costs

Costs of running workflows can vary wildly depending on the resources that are consumed and the size of the input data. In addition, the cost of cloud resources changes frequently.  As one point of reference, at the time of this writing an end-to-end immunogenomics workflow with exome, rnaseq, and neoantigen predictions costs in the neighborhood of 20 dollars when using preemptible nodes.


### Shared Helper Scripts

The README for each section includes instructions that go over
relevant helper scripts for that section. If you'd like to inspect the
helper scripts on their own, the best starting point is
[scripts/README.md](scripts/README.md)


### Docker Image

These scripts are contained within a Docker container image, to they
can be used asynchronously with bsub. This container image can be
found on dockerhub at `mgibio/cloudize-workflow`. Using latest is
always suggested but semantic versioning will be followed in case
prior behavior is needed.

After modifying any scripts, build and tag the docker image

    sh infra.sh build-and-tag VERSION

This command will create docker images with tags `VERSION` and `latest`



