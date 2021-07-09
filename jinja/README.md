# Jinja

Files in the `jinja/` directory are all related to defining a Google
deployment managing one compute VM for the Cromwell service.


# Performing the Deployments

Deployments refers to [Google Deployment Manager][google-deployment-manager].
Most interaction is going to be done through the command

    gcloud deployment-manager deployments

For more advanced/specific scenarios, the command should be used
directly. For the majority of the cases, the `infra.sh` script
commands `create-deploy`, `update-deploy` should be used.


# What do the files each do?

## deployment.yaml

This is essentially our entrypoint and where variable values are kept,
beneath the resources.properties path. This is the file sent to gcloud
deployment-manager as the configuration for the deployment. Certain
values within this file refer to existing infrastructure managed by
Terraform. Pull the outputs from Terraform to find their values.


## cromwell.jinja.schema

Inputs are defined here, as well as file imports. The only time this
file will change is if which files to import are changed, or if the
type/existence of any inputs change.


## cromwell.jinja

The actual resource definitions. Values within braces `{{ }}` are
interpolated from `deployment.yaml`. Files passed as metadata have
certain values string-replaced here, e.g. `replace("@CROMWELL-VERSION@", ...)`.
All such instances are `@` enclosed.


## cromwell.service

This file defines a systemd service unit for the Cromwell
service. This is what enables following logs with `journalctl` among
other conveniences.


## cromwell.conf

This file is the same here as anywhere else. This is the configuration
file for the Cromwell server. This file will have some values
interpolated within braces `{{ }}` and written to the metadata of the
created compute VM, to be used on startup.


## server_startup.py

This is the actual entrypoint for the compute VM, and is automatically
run when Google hands control of the booting VM back to us. It handles
additional setup like pulling the VM's metadata to write passed files
to disk, downloads dependencies like Cromwell jar, less, etc., and
starts the systemctl service.

[google-deployment-manager]:https://cloud.google.com/deployment-manager/docs
