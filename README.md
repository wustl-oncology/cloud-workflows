# cloudize-workflow.py script

A script is provided at `cloudize-workflow.py` to automate the
transition of a predefined workflow to use with the GCP Cromwell
server. Provided a bucket, CWL workflow definition, and inputs yaml,
the script will upload all specified File paths to the specified GCS
bucket, and generate a new inputs yaml with those file paths replaced
with their GCS path.

To use the script, make sure you're authenticated for the Google Cloud
CLI and have permissions to write to the specified bucket.

The command is as follows:

    python3 cloudize-workflow.py <bucket-name> /path/to/workflow.cwl /path/to/inputs.yaml

There is an optional argument to specify the path of your output file

    --output=/path/to/output

Files will be uploaded to a personal path, roughly
`gs://<bucket>/<whoami>/<date>/` and from that root will contain
whatever folder structure is shared, e.g. files `/foo/bar`,
`/foo/buux/baz` would upload to paths `gs://<bucket>/<whoami>/<date>/bar`
and `gs://<bucket>/<whoami>/<date>/buux/baz`

For now the script assumes a happy path. Files that don't exist will
be skipped and emit a warning. Uploads that fail with an exception
will cause the script to terminate early. Because of the by-date
personal paths, reattempted runs should overwrite existing files
instead of duplicating them.

Improvements to be done later regarding resilient uploads:
If one file fails, the remaining should still be attempted. For any
files the script fails to upload, either because the attempt failed or
because the program terminated early, persist that knowledge somewhere
and either expand or accompany this script with an uploading
reattempt.

## Dockerfile

There is a Dockerfile provided to work with `cloudize-workflow.py` in
storage1. It's extremely barebones -- it just copies the requirements,
pip installs them, copies the script, and runs it.

Because the Dockerfile is so barebones, there are additional
requirements for running it:
- Pass in the env var GOOGLE_APPLICATION_CREDENTIALS to auth the SDK
- Mount the volume(s) your workflow files are under
- Pass script arguments as if `docker run` were the script command

Luckily, LSF handles most of this through bsub. Excluding the more
general settings like memory, output, and user info, your bsub call
should look roughly like this. This assumes that LSF_DOCKER_VOLUMES
and GOOGLE_APPLICATION_CREDENTIALS are set accordingly
```
bsub -a 'docker(jackmaruska/cloudize-workflow:0.0.1)' 'python3 /opt/cloudize-workflow.py [script-args]'
```
The exact name of the docker image may change, or you can build and
push to your own Dockerhub repo.

# Interacting with Cromwell server

SSH in to server:
```
$ gcloud compute ssh "cromwell-server"
```
Assumes zone and region are set globally, otherwise those flags should
be specified.

Service can be interacted with via systemctl and journalctl
```
# Start server
systemctl start cromwell
# Restart server
systemctl restart cromwell
# Stop server
systemctl stop cromwell

# Follow logs
journalctl -u cromwell -f
```
For now those commands probably require a sudo. Hopefully fix that
later.

To troubleshoot starting script, its logs can be viewed with
```
sudo journalctl -u google-startup-scripts.service
```

Jobs should be submit either through REST API or through cromshell.
WDL file must specify task.runtime.docker to avoid an error

# Terraform

Infrastructure is managed as code through Terraform.

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


# Potential Additional Tools

### [Cromshell](https://github.com/broadinstitute/cromshell)
Submit Cromwell jobs from the shell.
Specify which server via env var `CROMWELL_URL`

### [WOMtool](https://cromwell.readthedocs.io/en/stable/WOMtool/)
Workflow Object Model tool. Almost all features WDL-only

### [Calrissian](https://github.com/Duke-GCB/calrissian)
CWL implementation inside a Kubernetes cluster. Alternative approach
that may yield a service with better scalability. Drawback is that it
seems to be fully eschewing Cromwell, which sinks interop with Terra
and other Cromwell-related tools.


# Acknowledgements

`server_startup.py` essentially forked from [Hall
Lab](https://github.com/hall-lab/cromwell-deployment/blob/b6a665b83b762b37c604f024517d7de683071aad/resources/startup-scripts/cromwell.py).
Some light refactoring and a few tweaks from breaking version updates.
