# Terraform

[Terraform][terraform-docs] is a declarative Infrastructure as Code
tools. In our case it's used to manage all of our infrastructure sans
a single compute VM instance, see directory `../jinja` for information
regarding that instance. Everything contained in this directory is a
fairly standard Terraform setup intended to be run on a local machine,
using a remote statefile stored in Google Cloud Storage (GCS).


# Authentication

Terraform actions are performed through the Terraform service account
for Google Cloud Platform (GCP). In order to use this service account,
you'll need a JSON file, `terraform-service-account.json`. This key
can be created in [the Service Account console][service-accounts].

You'll also need command-line [authentication for gcloud][auth-login].

    gcloud auth login

You may need to do some additional first-time configuration with
`gcloud config`.


# Setting Variables

Variables for Terraform can be passed in a few ways, but for
consistency it's recommended to do use `.tfvars` files. The repo
contains a `terraform.tfvars` for unsensitive values. Sensitive values
should be kept in an ignored file, `secrets.auto.tfvars` which
Terraform will load automatically. Sensitive variables are marked as
such in their definition within a `variables.tf`.


# Finding resource values

A small handful of resource values are needed outside of
Terraform. These values are defined in `output.tf` and can be viewed
with the following command

    terraform output

More detailed state information for troubleshooting can be seen using

    terraform show


# Changing Infrastructure

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


[terraform-docs]:https://www.terraform.io/docs/index.html
[service-accounts]:https://console.cloud.google.com/iam-admin/serviceaccounts/
[auth-login]:https://cloud.google.com/sdk/gcloud/reference/auth/login
[terraform-google]:https://registry.terraform.io/providers/hashicorp/google/latest/docs
