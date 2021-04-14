VM_NAME=cromwell
DB_INSTANCE=cromwell

case $1 in
    "thaw")
        echo "Thawing compute VM $VM_NAME"
        gcloud compute instances start $VM_NAME
        echo "Thawing database $DB_INSTANCE"
        gcloud sql instances patch $DB_INSTANCE --activation-policy ALWAYS
        ;;
    "freeze")
        echo "Freezing database $DB_INSTANCE"
        gcloud sql instances patch $DB_INSTANCE --activation-policy NEVER
        echo "Freezing compute VM $VM_NAME"
        gcloud compute instances stop $VM_NAME
        ;;
esac
