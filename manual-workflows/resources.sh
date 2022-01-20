#!/bin/bash

function show_help {
    echo "$0 - Create/Destroy resources for manual Cromwell workflow execution"
    echo ""
    echo "usage: sh $0 COMMAND --project <PROJECT> --bucket <BUCKET> [--email <EMAIL>]"
    echo ""
    echo "commands:"
    echo "    grant-user-permissions    Grant a new user required permissions to run workflows"
    echo "    revoke-user-permissions   Revoke permissions to run workflows from a user"
    echo "    init-project              Create required resources for the project"
    echo "    generate-cromwell-conf    Generate the cromwell.conf file required by the VM"
    echo "                              Use this when project init'd but no local copy"
    echo ""
    echo "arguments:"
    echo "    -h, --help     print this block"
    echo "    --bucket       name for the GCS bucket used by Cromwell"
    echo "    --project      name of your GCP project"
    echo "    --email        email of user to modify permissions. Only used on permissions commands."
    exit 0
}

COMMAND=$1; shift

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

if [ -z $PROJECT ]; then
    die 'ERROR: "--project" must be set.'
fi
if [ -z $BUCKET ]; then
    die 'ERROR: "--bucket" must be set.'
fi

COMPUTE_NAME="cromwell-compute"
SERVER_NAME="cromwell-server"
COMPUTE_ACCOUNT="$COMPUTE_NAME@$PROJECT.iam.gserviceaccount.com"
SERVER_ACCOUNT="$SERVER_NAME@$PROJECT.iam.gserviceaccount.com"

function generate_cromwell_conf {
    cp base_cromwell.conf cromwell.conf
    cat << EOF >> cromwell.conf
backend.providers.default.config {
    project = "$PROJECT"
    root = "gs://$BUCKET/cromwell-executions"
    genomics.compute-service-account = "$COMPUTE_ACCOUNT"
    filesystems.gcs.project = "$PROJECT"
}
EOF
}

sh ../scripts/enable_api.sh

case $COMMAND in
    "grant-user-permissions")
        if [ -z $EMAIL ]; then
            die 'ERROR: "--email" must be set.'
        fi
        gsutil iam ch user:$EMAIL:objectViewer gs://$BUCKET
        gsutil iam ch user:$EMAIL:objectCreator gs://$BUCKET
        gcloud projects add-iam-policy-binding $PROJECT \
               --member=user:$EMAIL \
               --role='roles/compute.instanceAdmin' > /dev/null
        gcloud projects add-iam-policy-binding $PROJECT \
               --member=user:$EMAIL \
               --role='roles/lifesciences.workflowsRunner' > /dev/null
        gcloud iam service-accounts add-iam-policy-binding $COMPUTE_ACCOUNT \
               --member=user:$EMAIL \
               --role='roles/iam.serviceAccountUser' > /dev/null
        echo ""
        ;;
    "revoke-user-permissions")
        if [ -z $EMAIL ]; then
            die 'ERROR: "--email" must be set.'
        fi
        gsutil iam ch -d user:$EMAIL gs://$BUCKET
        gcloud projects remove-iam-policy-binding $PROJECT \
               --member=user:$EMAIL \
               --role='roles/compute.instanceAdmin' > /dev/null
        gcloud projects remove-iam-policy-binding $PROJECT \
               --member=user:$EMAIL \
               --role='roles/lifesciences.workflowsRunner' > /dev/null
        gcloud iam service-accounts remove-iam-policy-binding $COMPUTE_ACCOUNT \
               --member=user:$EMAIL \
               --role='roles/iam.serviceAccountUser' \
               --project=$PROJECT > /dev/null
        echo ""
        ;;
    "init-project")
        # Create service accounts
        sh ../scripts/create_service_accounts.sh $PROJECT $SERVER_NAME $COMPUTE_NAME
        # Create bucket if not exists
        gsutil mb -p $PROJECT -b on gs://$BUCKET
        gsutil iam ch serviceAccount:$COMPUTE_ACCOUNT:objectAdmin gs://$BUCKET
        gsutil iam ch serviceAccount:$SERVER_ACCOUNT:objectAdmin gs://$BUCKET
        # Generate cromwell.conf
        generate_cromwell_conf
        ;;
    "generate-cromwell-conf")
        generate_cromwell_conf
        ;;
esac

cat <<EOF

Completed $COMMAND. Check stderr logs and make sure nothing unexpected
happened. Script optimistically executes and will relay gcloud's error on
redundant operations, e.g. creating a resource that already exists.

    Service Account: $SERVER_ACCOUNT

EOF
