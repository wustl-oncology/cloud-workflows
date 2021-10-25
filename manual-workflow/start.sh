# ensure bucket exists
# ensure compute service account exists
# ensure compute service account has permissions on bucket

gcloud compute instances create test-vm \
       --image-family ubuntu-2004-lts \
       --image-project ubuntu-os-cloud \
       --zone us-central1-c \
       --shielded-secure-boot \
       --confidential-compute --maintenance-policy=TERMINATE \
       --network=default --subnet=default \
       --metadata=cromwell-version=63 \
       --metadata-from-file=startup-script=server_startup.py,cromwell-conf=cromwell.conf,helpers-sh=helpers.sh
