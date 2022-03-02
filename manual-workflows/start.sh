SRC_DIR="$(dirname "${BASH_SOURCE[0]}")"

NETWORK=workflows
SUBNET=$NETWORK-cromwell

show_help () {
    cat <<EOF
$0 - Start a new Cromwell VM instance
usage: $0 INSTANCE_NAME [--argument value]*

arguments:
-h, --help         print this block and immediately exits
--project          GCP project name
--server-account   Email identifier of service account used by main Cromwell instance
--cromwell-conf    Local path to configuration file for Cromwell server. DEFAULT $SRC_DIR/cromwell.conf
--machine-type     GCP machine type for the instance. DEFAULT e2-standard-2

Additional arguments are passed directly to gsutil compute instances
create command. For more information on those arguments, check that commands
help page with

    gsutil compute instances create --help

EOF
}

die () {
    printf '%s\n\n' "$1" >&2
    show_help
    exit 1
}


INSTANCE_NAME=$1
if [ -z $INSTANCE_NAME ]; then
    show_help
    exit 1
fi
shift


while test $# -gt 0; do
    case $1 in
        -h|-\?|--help)
            show_help
            exit 0
            ;;
        --project*)
            if [ ! "$2" ]; then
                die 'Error: "--project" requires a string argument for the GCP project name used'
            else
                PROJECT=$2
                shift
            fi
            ;;
        --server-account*)
            if [ ! "$2" ]; then
                die 'ERROR: "--server-account" requires an email argument.'
            else
                SERVER_ACCOUNT=$2
                shift
            fi
            ;;
        --machine-type*)
            if [ ! "$2" ]; then
                die 'ERROR: "--machine-type" requires a string argument.'
            else
                MACHINE_TYPE=$2
                shift
            fi
            ;;
        *)
            break
            ;;
    esac
    shift
done

MACHINE_TYPE=${MACHINE_TYPE:-"e2-standard-2"}

[ -z $SERVER_ACCOUNT ] && die "Missing argument --server-account"
[ -z $PROJECT        ] && die "Missing argument --project"

CROMWELL_CONF="$SRC_DIR/cromwell.conf"
if [[ ! -f $CROMWELL_CONF ]]; then
    cat <<EOF
cromwell.conf does not exist. Check passed value or generate via

    sh resources.sh generate-config --project PROJECT --bucket BUCKET

EOF
    exit 1
fi

WORKFLOW_OPTIONS="$SRC_DIR/workflow_options.json"
if [[ ! -f $WORKFLOW_OPTIONS ]]; then
    cat <<EOF
workflow_options.json does not exist. Check passed value or generate via

    sh resources.sh generate-config --project PROJECT --bucket BUCKET

EOF
    exit 1
fi

gcloud compute instances create $INSTANCE_NAME \
       --project $PROJECT \
       --image-family debian-11 \
       --image-project debian-cloud \
       --zone us-central1-c \
       --machine-type=$MACHINE_TYPE \
       --service-account=$SERVER_ACCOUNT --scopes=cloud-platform \
       --network=$NETWORK --subnet=$SUBNET \
       --metadata=cromwell-version=71 \
       --metadata-from-file=startup-script=$SRC_DIR/server_startup.py,cromwell-conf=$CROMWELL_CONF,helpers-sh=$SRC_DIR/helpers.sh,cromwell-service=$SRC_DIR/cromwell.service,workflow-options=$WORKFLOW_OPTIONS \
       $@

cat <<EOF
To use this instance, SSH into it via:

    gcloud compute ssh $INSTANCE_NAME

To delete the instance when you're done:

    gcloud compute instances delete $INSTANCE_NAME

EOF
exit 0
