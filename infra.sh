VM_NAME=cromwell
DB_INSTANCE=cromwell

case $1 in
    "start")
        echo "Starting database $DB_INSTANCE"
        gcloud sql instances patch $DB_INSTANCE --activation-policy ALWAYS
        echo "Starting compute VM $VM_NAME"
        gcloud compute instances start $VM_NAME
        ;;
    "stop")
        echo "Stopping compute VM $VM_NAME"
        gcloud compute instances stop $VM_NAME
        echo "Stopping database $DB_INSTANCE"
        gcloud sql instances patch $DB_INSTANCE --activation-policy NEVER
        ;;
esac
