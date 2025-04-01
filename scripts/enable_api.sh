#!/bin/bash

# docs here: https://cloud.google.com/service-usage/docs/enable-disable
# for additional services, view `gcloud services list`
# they should all just be $SERVICE.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable batch.googleapis.com

