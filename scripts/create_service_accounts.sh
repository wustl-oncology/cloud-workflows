PROJECT=$1
SERVER_NAME=$2
COMPUTE_NAME=$3

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
