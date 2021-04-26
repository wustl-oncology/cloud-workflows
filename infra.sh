VM_NAME=cromwell
DB_INSTANCE=cromwell

case $1 in
    "thaw")
        echo "Thawing database $DB_INSTANCE"
        gcloud sql instances patch $DB_INSTANCE --activation-policy ALWAYS
        echo "Thawing compute VM $VM_NAME"
        gcloud compute instances start $VM_NAME
        ;;
    "freeze")
        echo "Freezing compute VM $VM_NAME"
        gcloud compute instances stop $VM_NAME
        echo "Freezing database $DB_INSTANCE"
        gcloud sql instances patch $DB_INSTANCE --activation-policy NEVER
        ;;
esac
