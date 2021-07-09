# Usage

Most interaction with the Cromwell server will be one of
1. Preparing a workflow for submission
2. Submitting that workflow
3. Querying/fetching its output

## Preparing a workflow for submission

### Staging Input Files

To submit a workflow to the cloud Cromwell server, all its input files
must be located on a GCS cloud bucket the server has access to. In
this case most likely `griffith-lab-cromwell`. A helper script,
`scripts/cloudize-workflow.py` will handle this step. It parses a
workflow definition (either CWL or WDL), finds all the File inputs,
uploads them, and generates a new workflow inputs file with the new
cloud paths.

    python3 scripts/cloudize-workflow.py \
        griffith-lab-cromwell
        /path/to/workflow/definition \
        /path/to/workflow/inputs

See the script's documentation or help message for more details.

### Zip Dependencies

When running on the cloud, workflow dependencies must be zipped to be
sent along with the root workflow.

Zipping is kind of finnicky and is best automated as done through
`scripts/submit_workflow.sh`.

Assuming a file structure as in analysis-workflows:

For WDL files, zip the `definitions` directory. Modify calling workflow
file to remove relative imports, they're disallowed.

    cd analysis-wdls/definitions
    zip -r $ZIP .

For CWL files, there are two options. Either do the same as WDL above,
_or_ zip the directory containing your workflow, and its parent, so
those relative paths become available in the zip.

    cd analysis-workflows/definitions/pipelines
    zip -r $ZIP . ..

## Submitting that workflow

To submit a workflow to the server, send a POST request to
`$CROMWELL_URL/api/workflows/v1`. There are many options for doing
this POST request but the main ones are:

a) Use the [Swagger endpoint][swagger-endpoint]
b) modify the `scripts/submit_workflow.sh` to work in your setup, this
will handle both zip and curl.
c) use your preferred zip+curl equivalent

### Cromshell

Cromshell is very useful for interacting with a Cromwell server if
you're more comfortable on the command-line or want to automate any of
the interactions. The drawback is that some parts of it like workflow
submit only work with WDL.


## Querying/Fetching its output

As above, anything that means "send equivalent request to server" will
do for things like checking status or locations of outputs. For
helpers that will actually retrieve the files for you,
`scripts/pull_outputs.py` will request the locations of all outputs
and download them. Cromshell is most useful in this space.

# Terraform

[Terraform][terraform-docs] is a declarative Infrastructure as Code
tools. In our case it's used to manage all of our infrastructure sans
a single compute VM instance, see directory `../jinja` for information
regarding that instance. Everything contained in this directory is a
fairly standard Terraform setup intended to be run on a local machine,
using a remote statefile stored in Google Cloud Storage (GCS).

## Authentication

Terraform actions are performed through the Terraform service account
for Google Cloud Platform (GCP). In order to use this service account,
you'll need a JSON file, `terraform-service-account.json`. This key
can be created in [the Service Account console][service-accounts].

If this service account doesn't yet exist, it needs the following
privileges:
    - Editor
    - Security Admin
    - Project IAM Admin

You'll also need command-line [authentication for gcloud][auth-login].

    gcloud auth login

You may need to do some additional first-time configuration with
`gcloud config`.

## Setting Variables

Variables for Terraform can be passed in a few ways, but for
consistency it's recommended to do use `.tfvars` files. The repo
contains a `terraform.tfvars` for unsensitive values. Sensitive values
should be kept in an ignored file, `secrets.auto.tfvars` which
Terraform will load automatically. Sensitive variables are marked as
such in their definition within a `variables.tf`.

## Finding resource values

A small handful of resource values are needed outside of
Terraform. These values are defined in `output.tf` and can be viewed
with the following command

    terraform output

More detailed state information for troubleshooting can be seen using

    terraform show

## Changing Infrastructure

Without delving into a full tutorial of how Terraform works which is
available with [their docs][terraform-docs], the main relevant points
are that nearly every cloud resource has a 1:1 mapping with the
[Google provider][terraform-google]. Changes to existing resources, or
creation of new resources, is probably just going to be done directly
off of those docs.

Make use of modules as necessary to abstract relevant blocks of
infrastructure. Each directory within this dir including itself
contain up to three .tf files: `main.tf`, `variables.tf`, and
`output.tf`. They may or may not contain directories with the same
constraints. Those directories are modules to separate concerns. See
any of the existing modules for examples.

After changes have been made, a combination of `terraform plan` and
`terraform apply` should be used. `plan` for spot-checking as changes
are made that what will happen is expected, and `apply` to actually
persist those changes. `apply` will perform the same action as `plan`
as a preliminary step.

As needed, there are options to the command to only target certain
resources, use alternate variable settings, auto-approve, etc.

# Jinja

Files in the `jinja/` directory are all related to defining a Google
deployment managing one compute VM for the Cromwell service.

## Performing the Deployments

Deployments refers to [Google Deployment Manager][google-deployment-manager].
Most interaction is going to be done through the command

    gcloud deployment-manager deployments

For more advanced/specific scenarios, the command should be used
directly. For the majority of the cases, the `infra.sh` script
commands `create-deploy`, `update-deploy` should be used.

## What do the files each do?
### deployment.yaml

This is essentially our entrypoint and where variable values are kept,
beneath the resources.properties path. This is the file sent to gcloud
deployment-manager as the configuration for the deployment. Certain
values within this file refer to existing infrastructure managed by
Terraform. Pull the outputs from Terraform to find their values.

### cromwell.jinja.schema

Inputs are defined here, as well as file imports. The only time this
file will change is if which files to import are changed, or if the
type/existence of any inputs change.

### cromwell.jinja

The actual resource definitions. Values within braces `{{ }}` are
interpolated from `deployment.yaml`. Files passed as metadata have
certain values string-replaced here, e.g. `replace("@CROMWELL-VERSION@", ...)`.
All such instances are `@` enclosed.

### cromwell.service

This file defines a systemd service unit for the Cromwell
service. This is what enables following logs with `journalctl` among
other conveniences.

### cromwell.conf

This file is the same here as anywhere else. This is the configuration
file for the Cromwell server. This file will have some values
interpolated within braces `{{ }}` and written to the metadata of the
created compute VM, to be used on startup.

### server_startup.py

This is the actual entrypoint for the compute VM, and is automatically
run when Google hands control of the booting VM back to us. It handles
additional setup like pulling the VM's metadata to write passed files
to disk, downloads dependencies like Cromwell jar, less, etc., and
starts the systemctl service.

[google-deployment-manager]:https://cloud.google.com/deployment-manager/docs
[auth-login]:https://cloud.google.com/sdk/gcloud/reference/auth/login
[service-accounts]:https://console.cloud.google.com/iam-admin/serviceaccounts/
[swagger-endpoint]:http://35.188.155.31:8000/swagger/index.html?url=/swagger/cromwell.yaml
[terraform-docs]:https://www.terraform.io/docs/index.html
[terraform-google]:https://registry.terraform.io/providers/hashicorp/google/latest/docs

# Scripts

Some helper scripts for interacting with the Cromwell server.

## pull\_outputs.py

pull_outputs.py will query a Cromwell server for the outputs
associated with a workflow, and download them. For details on usage,
see `python3 scripts/pull_outputs.py --help`.

Requirements to run this script:
 - able to reach the Cromwell server's endpoints
 - authenticated by Google
 - authorized to read files from specified GCS bucket

## cloudize-workflow.py

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

## submit_workflow.sh

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

## Docker Image

These scripts are contained within a Docker container image, to they
can be used asynchronously with bsub. This container image can be
found on dockerhub at `jackmaruska/cloudize-workflow`. Using latest is
always suggested but semantic versioning will be followed in case
prior behavior is needed.
