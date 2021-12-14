#!/bin/bash

function show_help {
    echo "$0 - One-time setup to create resources required by GMS to run workflows"
    echo "usage: $0 --project PROJECT --bucket BUCKET"
    echo ""
    echo "arguments:"
    echo "-h, --help     print this block and immediately exit"
    echo "--project      name of the Google Cloud Project to create resources"
    echo "--bucket       name to use for GCS bucket"
    echo ""
    echo "All arguments (besides help) are required and have an associated value. None are flags."
    echo ""
    echo "No guards in place for existing objects. Resource already exists messages"
    echo "in stderr may be ignored."
}

function die {
    printf '%s\n' "$1" >&2
    show_help
    exit 1
}

while test $# -gt 0; do
    case $1 in
        -h|-\?|--help)
            show_help
            exit 0
            ;;
        --project*)
            if [ -z "$2" ]; then
                die 'ERROR: "--project" requires non-empty string argument.'
            else
                PROJECT=$2
                shift
            fi
            ;;
        --bucket*)
            if [ -z "$2" ]; then
                die 'ERROR: "--bucket" requires non-empty string argument.'
            else
                BUCKET=$2
                shift
            fi
            ;;
    esac
    shift
done
[ -z $BUCKET ] && die 'Missing --bucket argument.'
[ -z $PROJECT ] && die 'Missing --project argument.'

COMPUTE_NAME="cromwell-compute"
SERVER_NAME="cromwell-server"
COMPUTE_ACCOUNT="$COMPUTE_NAME@$PROJECT.iam.gserviceaccount.com"
SERVER_ACCOUNT="$SERVER_NAME@$PROJECT.iam.gserviceaccount.com"

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

# Task compute VM service account
gcloud iam service-accounts create $COMPUTE_NAME \
       --display-name="Cromwell Task Compute VM" \
       --project=$PROJECT
gcloud iam service-accounts add-iam-policy-binding $COMPUTE_ACCOUNT \
       --member="serviceAccount:$SERVER_ACCOUNT" \
       --project=$PROJECT \
       --role='roles/iam.serviceAccountUser' > /dev/null

# Create bucket
gsutil mb -b on gs://$BUCKET
# Service account can use bucket
gsutil iam ch serviceAccount:$COMPUTE_ACCOUNT:objectAdmin gs://$BUCKET
gsutil iam ch serviceAccount:$SERVER_ACCOUNT:objectAdmin gs://$BUCKET
