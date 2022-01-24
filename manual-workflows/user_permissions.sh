#!/bin/bash

function show_help {
    cat <<EOF
$0 - Grant/Revoke permissions to a user (not service account!)

usage: sh $0 COMMAND --project <PROJECT> --bucket <BUCKET> --email <EMAIL>

commands:
    grant    Grant a new user required permissions to run workflows. Do not run on a service account.
    revoke   Revoke permissions to run workflows from a user. Do not run on a service account.

arguments:
    -h, --help     print this block
    --bucket       name for the GCS bucket used by Cromwell
    --project      name of your GCP project
    --email        email of user to modify permissions
EOF
    exit 0
}

COMMAND=$1; shift

SERVER_ACCOUNT="cromwell-server@$PROJECT.iam.gserviceaccount.com"

# die and opts based on this example
# http://mywiki.wooledge.org/BashFAQ/035
# --long-opt* example here
# https://stackoverflow.com/a/7069755
function die {
    printf '%s\n' "$1" >&2 && exit 1
}

while test $# -gt 0; do
    case $1 in
        -h|--help)
            show_help
            exit
            ;;
        --bucket*)
            if [ ! "$2" ]; then
                die 'ERROR: "--bucket" requires a non-empty argument.'
            else
                BUCKET=$2
                shift
            fi
            ;;
        --email*)
            if [ ! "$2" ]; then
                die 'ERROR: "--email" requires a non-empty argument.'
            else
                EMAIL=$2
                shift
            fi
            ;;
        --project*)
            if [ ! "$2" ]; then
                die 'ERROR: "--project" requires a non-empty argument.'
            else
                PROJECT=$2
                shift
            fi
            ;;
        *)
            break
            ;;
    esac
    shift
done

[ -z $PROJECT ] && die 'ERROR: "--project" must be set.'
[ -z $BUCKET  ] && die 'ERROR: "--bucket" must be set.'
[ -z $EMAIL   ] && die 'ERROR: "--email" must be set.'

case $COMMAND in
    "grant")
        gsutil iam ch user:$EMAIL:objectAdmin gs://$BUCKET
        gcloud projects add-iam-policy-binding $PROJECT \
               --member=user:$EMAIL \
               --role='roles/compute.instanceAdmin' > /dev/null
        gcloud projects add-iam-policy-binding $PROJECT \
               --member=user:$EMAIL \
               --role='roles/lifesciences.workflowsRunner' > /dev/null
        gcloud iam service-accounts add-iam-policy-binding $SERVER_ACCOUNT \
               --member=user:$EMAIL \
               --role='roles/iam.serviceAccountUser' > /dev/null
        echo ""
        ;;
    "revoke")
        gsutil iam ch -d user:$EMAIL gs://$BUCKET
        gcloud projects remove-iam-policy-binding $PROJECT \
               --member=user:$EMAIL \
               --role='roles/compute.instanceAdmin' > /dev/null
        gcloud projects remove-iam-policy-binding $PROJECT \
               --member=user:$EMAIL \
               --role='roles/lifesciences.workflowsRunner' > /dev/null
        gcloud iam service-accounts remove-iam-policy-binding $SERVER_ACCOUNT \
               --member=user:$EMAIL \
               --role='roles/iam.serviceAccountUser' \
               --project=$PROJECT > /dev/null
        echo ""
        ;;
esac
