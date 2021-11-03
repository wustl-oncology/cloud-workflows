SRC_DIR="$(dirname "${BASH_SOURCE[0]}")"

INSTANCE_NAME=$1
if [ -z $INSTANCE_NAME ]; then
    echo "ERROR: must set instance name."
    echo "usage: sh $0 INSTANCE"
    exit 1
fi

CROMWELL_CONF=${2:-"$SRC_DIR/cromwell.conf"}
if [ ! -f $CROMWELL_CONF ]; then
    echo "cromwell.conf does not exist. Check passed value or generate via"
    echo ""
    echo "    sh resources.sh generate-cromwell-conf --project PROJECT --bucket BUCKET"
    echo ""
    exit 1
fi

gcloud compute instances create $INSTANCE_NAME \
       --image-family ubuntu-2004-lts \
       --image-project ubuntu-os-cloud \
       --zone us-central1-c \
       --shielded-secure-boot \
       --confidential-compute --maintenance-policy=TERMINATE \
       --network=default --subnet=default \
       --metadata=cromwell-version=63 \
       --metadata-from-file=startup-script=$SRC_DIR/server_startup.py,cromwell-conf=$CROMWELL_CONF,helpers-sh=$SRC_DIR/helpers.sh

echo "To use this instance, SSH into it via:"
echo ""
echo "    gcloud compute ssh $INSTANCE_NAME"
echo ""
echo "To delete the instance when you're done:"
echo ""
echo "    gcloud compute instances delete $INSTANCE_NAME"
echo ""
exit 0
