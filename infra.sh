VM_NAME=cromwell

DB_INSTANCE=cromwell1
DEPLOY_NAME=cromwell
DOCKER_IMAGE=jackmaruska/cloudize-workflow

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
        gcloud deployment-manager deployments create $DEPLOY_NAME --config $SRC_DIR/central-server/jinja/deployment.yaml
        ;;
    "update-deploy")
        echo "Updating previous deployment"
        gcloud deployment-manager deployments update $DEPLOY_NAME --config $SRC_DIR/central-server/jinja/deployment.yaml
        ;;
    "build-and-tag")
        echo "Building container image tagged latest"
        docker build $SRC_DIR -t $DOCKER_IMAGE:latest
        # this one will be cached, basically just doing a tag without having to find image ID
        echo "Building container image tagged $2"
        docker build $SRC_DIR -t $DOCKER_IMAGE:$2

        echo "Pushing container image tagged latest"
        docker push $DOCKER_IMAGE:latest
        echo "Pushing container image tagged $2"
        docker push $DOCKER_IMAGE:$2
        ;;
esac
