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
For now those commands probably require a sudo. Hopefully fix that later.


# TODO
- [ ] Terraform pull project-id, location from provider instead of locals
- [ ] Terraform move non-derived locals to variables
- [ ] GCP when do we want a network vs a subnetwork?
- [ ] Terraform additional parameters to boot_disk
