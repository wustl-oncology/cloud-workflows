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

# Using central server with a separate lab

TODO: why you should do this

## Add a backend provider

The server uses the configuration file `jinja/cromwell.conf`.

Under the path `backend.providers` add a new entry with configuration
for the new lab.

```conf
...
backend {
  ...
  providers  {
    <NewProviderName> {
      actor-factory = "cromwell.backend.google.pipelines.v2beta.PipelinesApiLifecycleActorFactory"
      config {
        project = <google-project-name>
        root = <gcs-path>
        genomics {
          auth = "application-default"
          compute-service-account = "<service-account-email>"
          endpoint-url = "https://lifesciences.googleapis.com/"
          location = "us-central1"
        }

        filesystems {
          gcs {
            auth = "application-default"
            project = <google-project-name>
            caching {
              duplication-strategy = "reference"
            }
          }
        }
        include "papi_v2_reference_image_manifest.conf"
      }

    }
  }
  ...
}
...
```

Values within brackets need to be changed for each new lab.


- NewProviderName

Use the name for whatever group is associated with this
configuration. This value is used in workflow-options.json to change
which provider is used.

- google-project-name

Cromwell will refer to a GCS bucket or other resources. This is just
the name of your GCP project as it appears in the console or CLI.

- gcs-path

Whatever GCS path to store Cromwell generated files. Constraint that
service-account-email must be able to write to this bucket. A sub-path
can be included if the bucket will be used for other files,
e.g. inputs.

- service-account-email

Email address to a service account granted permissions required by the
compute VMs. It should have a role of "iam.serviceAccountUser" and
permissions to read/write on the bucket in gcs-path.

## Checklist

- [ ] Cloud Life Sciences API Enabled
- [ ] Created a compute service account with project role Service Account
      User and member permissions granting a role Service Account User
      to the central server service account
- [ ] Project IAM permissions for Cromwell server, role Life Sciences
      Workflow Runner
- [ ] Bucket created with role Storage Object Creator granted to your
      compute and central server service accounts
- [ ] Add your lab to Griffith Lab owned resources
  + [ ] Configuration added to server .conf
  + [ ] Service account email added to Terraform vars  (maybe?)
- [ ] Specifying backend in submissions with workflow_options.json
      (see which keys needed)

Central server service account:
`cromwell-server@griffith-lab.iam.gserviceaccount.com`
