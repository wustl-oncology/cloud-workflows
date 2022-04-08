#!/usr/bin/bash

PROJECT=$1
SERVER_NAME=$2
COMPUTE_NAME=$3
BUCKET=$4

NETWORK=cloud-workflows
SUBNET=cloud-workflows-default

COMPUTE_ACCOUNT="$COMPUTE_NAME@$PROJECT.iam.gserviceaccount.com"
SERVER_ACCOUNT="$SERVER_NAME@$PROJECT.iam.gserviceaccount.com"

WASHU_CIDR="128.252.0.0/16"
WASHU2_CIDR="65.254.96.0/19"

# Cromwell server VM service account
gcloud iam service-accounts create $SERVER_NAME \
       --display-name="Cromwell Server VM" \
       --project=$PROJECT
gcloud projects add-iam-policy-binding $PROJECT \
       --member="serviceAccount:$SERVER_ACCOUNT" \
       --role='roles/lifesciences.workflowsRunner' > /dev/null
gcloud projects add-iam-policy-binding $PROJECT \
       --member="serviceAccount:$SERVER_ACCOUNT" \
       --role='roles/compute.instanceAdmin' > /dev/null
gcloud projects add-iam-policy-binding $PROJECT \
       --member="serviceAccount:$SERVER_ACCOUNT" \
       --role='roles/iam.serviceAccountUser' > /dev/null

# Task compute VM service account
gcloud iam service-accounts create $COMPUTE_NAME \
       --display-name="Cromwell Task Compute VM" \
       --project=$PROJECT
gcloud iam service-accounts add-iam-policy-binding $COMPUTE_ACCOUNT \
       --member="serviceAccount:$SERVER_ACCOUNT" \
       --project=$PROJECT \
       --role='roles/iam.serviceAccountUser' > /dev/null


# Network
gcloud compute networks create $NETWORK \
       --project=$PROJECT \
       --subnet-mode=custom

# Subnet
gcloud compute networks subnets create $SUBNET \
       --project=$PROJECT \
       --range="10.10.0.0/16" \
       --region="us-central1" \
       --network=$NETWORK

# Firewall
gcloud compute firewall-rules create $NETWORK-allow-ssh \
       --project=$PROJECT \
       --source-ranges $WASHU_CIDR,$WASHU2_CIDR \
       --network=$NETWORK \
       --allow tcp:22

# Bucket
gsutil mb -p $PROJECT -b on gs://$BUCKET
gsutil iam ch serviceAccount:$COMPUTE_ACCOUNT:objectAdmin gs://$BUCKET
gsutil iam ch serviceAccount:$COMPUTE_ACCOUNT:legacyBucketOwner gs://$BUCKET
gsutil iam ch serviceAccount:$SERVER_ACCOUNT:objectAdmin gs://$BUCKET
gsutil iam ch serviceAccount:$SERVER_ACCOUNT:legacyBucketOwner gs://$BUCKET
