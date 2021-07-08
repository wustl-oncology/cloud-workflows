VM_NAME=cromwell

DB_INSTANCE=cromwell1
DEPLOY_NAME=cromwell

SRC_DIR="$(dirname "${BASH_SOURCE[0]}")"

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
    "create-deploy")
        echo "Creating new deployment"
        gcloud deployment-manager deployments create $DEPLOY_NAME --config $SRC_DIR/jinja/deployment.yaml
        ;;
    "update-deploy")
        echo "Updating previous deployment"
        gcloud deployment-manager deployments update $DEPLOY_NAME --config $SRC_DIR/jinja/deployment.yaml
esac
