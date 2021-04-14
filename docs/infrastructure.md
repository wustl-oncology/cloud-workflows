# Managed Infrastructure

The resources required by this repository have a split between
Terraform and Google Deployment Manager. Everything that can be
represented in Terraform is located there, and the Google Deployment
Manager contains only the Cromwell server Compute VM instance.

## Terraform

### Requirements
1. Standard Terraform installation via their docs
1. a service account for Terraform with privileges:
  - Editor
  - Security Admin
  - Project IAM Admin
1. credentials to Terraform service account saved to
   `terraform/terraform-service-account.json`

Additionally, there are inputs in `terraform/variables.tf` which must
be specified on run. There are several approaches to handling input
variables, specified [here](https://www.terraform.io/docs/language/values/variables.html#assigning-values-to-root-module-variables).
Input variables may be sensitive (as marked in variables.tf) and
if stored locally should be managed as any other local secrets would.

### Secrets Management

Secrets must be specified to certain Terraform resources like database
instances. There are two ways these secrets need to be locked down in
Terraform.

First, Terraform sometimes prints out results for
resources. To prevent sensitive values from printing, those variables
must be marked with `sensitive = true`. Provider resources have this
for variables they deem sensitive.

Second, Terraform persists resource states in a .tfstate file. This is
critical to the functioning of Terraform, so the values can't be
prevented from reaching this point or scrubbed from it. Instead, keep
this file locked down. The state file for Terraform is stored in GCS,
encrypted, and accessible only to those with permissions for the state
bucket. In this way, access to the terraform state files are defacto
access to the values of all secrets used in Terraform. Keep access to
this bucket _severely_ restricted.

## Why is the compute VM managed separately from the other resources?

This was the easiest approach to avoiding persistence of secret values
in the Terraform state/output in an insensitive way.

The compute VM instance is passed secret values via metadata on the
resource. Specifically its value is inserted into script
contents. These script contents will be persisted to Terraform state
without the sensitive tag which prevents them from being inspected, as
normally happens for these vars.

Using Google Deployment Manager with Jinja templating avoids this
problem completely because there is no persistence mechanism.

The drawback to both of these approaches is that the script contents
can still be seen on the console. The solution to this would be to
store the key in Google Key Management System and have the startup
script pull that value. This introduces extra complexity on setup,
however, so it's not been applied at this early stage.


## Potential Improvements

- Network security. Hide behind WashU VPN
- Leverage Key Management Service. Allows removal of Jinja, adds
  manual constraint.


## Acknowledgements

Contents of `jinja` directory is a stripped down version of [Hall Lab
Cromwell Deployment](https://github.com/hall-lab/cromwell-deployment/tree/b6a665b83b762b37c604f024517d7de683071aad).
