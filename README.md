# Terraform Requirements

1. Standard Terraform installation via their docs
1. a service account for Terraform with privileges:
    - Editor
    - Security Admin
    - Project IAM Admin
1. credentials to Terraform service account saved to
   `terraform-service-account.json`

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

# Using the Cromwell Terraform module

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
