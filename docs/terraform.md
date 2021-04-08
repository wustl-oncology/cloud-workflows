# Terraform

~~Infrastructure is managed as code through Terraform.~~
Infrastructure was previously managed through
Terraform. Infrastructure is now managed through the [Hall Lab
Cromwell Deployment repo](https://github.com/hall-lab/cromwell-deployment)
.

This document is being kept around for archaeological purposes, in
case it becomes relevant again. The reason for scrapping Terraform in
favor of the Hall Lab approach is mostly around secrets
handling. Terraform creates resources declaratively, so the password
to the database must be known when running the application. One of the
main goals of using Terraform was minimal input requirements from the
user. To support that goal, we tried generating the secrets
declaratively, but the random generators would return different values
each run and always try to replace resources, leading to a lot of
noise and churn. It's possible that reasons to use Terraform over the
scripted approach will come up and this may be reattempted then. For
now, though, the Hall Lab approach was chosen for simplicity.


## Requirements
1. Standard Terraform installation via their docs
1. a service account for Terraform with privileges:
    - Editor
    - Security Admin
    - Project IAM Admin
1. credentials to Terraform service account saved to
   `terraform-service-account.json`


## Secrets Management

Secrets must be specified to Terraform resource via a secure
mechanism, likely either KMS or secret manager.

Terraform will sometimes print out and will always store in state all
values used to generate infrastructure, including secrets. To address
these behaviors, we'll use the `sensitive` flag on TF variables and
use an encrypted remote state on GCS to store the state.

Terraform has a feature to specify `sensitive = true` and do some of
its own management. This mostly just prevents accidental exposure
while using the tool. The secret must be stored in a secure system
like KMS or secret manager.

Terraform state is stored securely, encrypted by default, in
GCS. Access to the state file and thus the ability to decrypt the
state file is associated with access permissions around the
bucket. Anyone with access to view the bucket will be able to view
secrets, so permissions around that bucket have been restricted to
project owners and the terraform service account.


## Using the Cromwell module

(Once this repo hits GitHub) Terraform should be able to reference the
Cromwell module via its Git SHA URL, and be called as in
`main.tf`. Check `variables.tf` and `output.tf` for usage.


# Potential Gotchas

As of 2021-03-22 the cromwell.conf file does not contain all settings
required to run Cromwell locally -- some are in Terraform
(cromwell/server/main.tf). This may be tweaked later but for now just
run off of a derived .conf file that includes the Terraformed settings.


# Potential Future Improvements

- Docker image to pre-build contents of `server_startup.py`
- Metadata database for Cromwell
- Hide server behind WashU VPN
- larger project of surrounding ecosystem


# Acknowledgements

`server_startup.py` essentially forked from [Hall
Lab](https://github.com/hall-lab/cromwell-deployment/blob/b6a665b83b762b37c604f024517d7de683071aad/resources/startup-scripts/cromwell.py).
Some light refactoring and a few tweaks from breaking version updates.
