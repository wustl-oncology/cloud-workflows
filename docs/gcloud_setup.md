# Install Google Cloud CLI

On compute1 clients it should already be installed.

To work from a docker container, the image `google/cloud-sdk:latest`
can be used.

To work from a local machine, use your package manager to install
it. For MacOS the command is

    brew install --cask google-cloud-sdk

This package will give you access to the commands `gcloud` and
`gsutil`.

# Authenticate with Google Cloud CLI

Log in through Google with your WashU account

    gcloud auth login

They'll provide a link which sends you to Google authentication, and
will either automatically log in on verification, or provide a code
for the terminal prompt.

Once you're logged in, set your project and zone. If you don't know
your project name, it can be viewed at
[console.cloud.google.com](https://console.cloud.google.com) in the top-left
corner, in a dropdown menu of your account's projects. The value
should be from the `id` column. Google separates the concept of a
projects name, its ID, and its _numerical_ ID. The name and numerical
ID values will not work here.

    gcloud config set project PROJECT-ID
    gcloud config set zone us-central1-c

This should only need to be done once per machine. If you change which
client you use on compute1 then you may need to run these commands again.

# Maintain these credentials in a Docker image

The easiest way to stay logged in with Docker is to mount
`~/.config/gcloud` to the container. In the case of this image, which
defaults to the root user, this command should suffice

```
docker run [OPTS] -v ~/.config/gcloud:/root/.config/gcloud COMMAND
```
Optionally replacing [OPTS] and COMMAND with your specifics as needed,
e.g. to jump in to an interactive session,
```
docker run -it -v ~/.config/gcloud:/root/.config/gcloud /bin/bash
```
