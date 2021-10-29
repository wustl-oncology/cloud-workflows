SRC_DIR="$(dirname "${BASH_SOURCE[0]}")"

# ensure bucket exists
# ensure compute service account exists
# ensure compute service account has permissions on bucket
INSTANCE_NAME=$1
CROMWELL_CONF=${2:-"$SRC_DIR/cromwell.conf"}

gcloud compute instances create $INSTANCE_NAME \
       --image-family ubuntu-2004-lts \
       --image-project ubuntu-os-cloud \
       --zone us-central1-c \
       --shielded-secure-boot \
       --confidential-compute --maintenance-policy=TERMINATE \
       --network=default --subnet=default \
       --metadata=cromwell-version=63 \
       --metadata-from-file=startup-script=$SRC_DIR/server_startup.py,cromwell-conf=$CROMWELL_CONF,helpers-sh=$SRC_DIR/helpers.sh
