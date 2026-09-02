#!/usr/bin/bash

PROJECT=$1
SERVER_NAME=$2
COMPUTE_NAME=$3
BUCKET=$4
IP_RANGE=$5
GC_REGION=$6
RETENTION=$7

NETWORK=cloud-workflows
SUBNET=cloud-workflows-default

COMPUTE_ACCOUNT="$COMPUTE_NAME@$PROJECT.iam.gserviceaccount.com"
SERVER_ACCOUNT="$SERVER_NAME@$PROJECT.iam.gserviceaccount.com"

# WASHU_CIDR="128.252.0.0/16"
# WASHU2_CIDR="65.254.96.0/19"

# Cromwell server VM service account
gcloud iam service-accounts create $SERVER_NAME \
       --display-name="Cromwell Server VM" \
       --project=$PROJECT
gcloud projects add-iam-policy-binding $PROJECT \
       --member="serviceAccount:$SERVER_ACCOUNT" \
       --role='roles/batch.jobsEditor' > /dev/null
gcloud projects add-iam-policy-binding $PROJECT \
       --member="serviceAccount:$SERVER_ACCOUNT" \
       --role='roles/batch.agentReporter' > /dev/null
gcloud projects add-iam-policy-binding $PROJECT \
       --member="serviceAccount:$SERVER_ACCOUNT" \
       --role='roles/compute.instanceAdmin' > /dev/null
gcloud projects add-iam-policy-binding $PROJECT \
       --member="serviceAccount:$SERVER_ACCOUNT" \
       --role='roles/iam.serviceAccountUser' > /dev/null
gcloud projects add-iam-policy-binding $PROJECT \
       --member="serviceAccount:$SERVER_ACCOUNT" \
       --role='roles/logging.logWriter' > /dev/null

# Task compute VM service account
gcloud iam service-accounts create $COMPUTE_NAME \
       --display-name="Cromwell Task Compute VM" \
       --project=$PROJECT
gcloud iam service-accounts add-iam-policy-binding $COMPUTE_ACCOUNT \
       --member="serviceAccount:$SERVER_ACCOUNT" \
       --project=$PROJECT \
       --role='roles/iam.serviceAccountUser' > /dev/null

gcloud projects add-iam-policy-binding $PROJECT \
       --member="serviceAccount:$COMPUTE_ACCOUNT" \
       --role='roles/batch.jobsEditor' > /dev/null
gcloud projects add-iam-policy-binding $PROJECT \
       --member="serviceAccount:$COMPUTE_ACCOUNT" \
       --role='roles/batch.agentReporter' > /dev/null
gcloud projects add-iam-policy-binding $PROJECT \
       --member="serviceAccount:$COMPUTE_ACCOUNT" \
       --role='roles/compute.instanceAdmin' > /dev/null

# Network
gcloud compute networks create $NETWORK \
       --project=$PROJECT \
       --subnet-mode=custom

# Subnet
gcloud compute networks subnets create $SUBNET \
       --project=$PROJECT \
       --range="10.10.0.0/16" \
       --region=$GC_REGION \
       --network=$NETWORK

# Firewall
gcloud compute firewall-rules create $NETWORK-allow-ssh \
       --project=$PROJECT \
       --source-ranges $IP_RANGE \
       --network=$NETWORK \
       --allow tcp:22

# Bucket
if [ ! -z $RETENTION ]; then
    gcloud storage buckets create gs://$BUCKET --project=$PROJECT --location=$GC_REGION --uniform-bucket-level-access --retention-period=$RETENTION
else
    gcloud storage buckets create gs://$BUCKET --project=$PROJECT --location=$GC_REGION --uniform-bucket-level-access
fi
gcloud storage buckets add-iam-policy-binding gs://$BUCKET --member=serviceAccount:$COMPUTE_ACCOUNT --role=roles/storage.objectAdmin
gcloud storage buckets add-iam-policy-binding gs://$BUCKET --member=serviceAccount:$COMPUTE_ACCOUNT --role=roles/storage.legacyBucketOwner
gcloud storage buckets add-iam-policy-binding gs://$BUCKET --member=serviceAccount:$SERVER_ACCOUNT --role=roles/storage.objectAdmin
gcloud storage buckets add-iam-policy-binding gs://$BUCKET --member=serviceAccount:$SERVER_ACCOUNT --role=roles/storage.legacyBucketOwner
gcloud storage buckets update gs://$BUCKET --public-access-prevention
