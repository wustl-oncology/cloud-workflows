#!/usr/bin/bash

SRC_DIR="$(dirname "${BASH_SOURCE[0]}")"

NETWORK=cloud-workflows
SUBNET=cloud-workflows-default

show_help () {
    cat <<EOF
$0 - Start a new Cromwell VM instance
usage: $0 INSTANCE_NAME [--argument value]*

arguments:
-h, --help           prints this block and immediately exits
--project            GCP project name
--server-account     Email identifier of service account used by main Cromwell instance
--cromwell-conf      Local path to configuration file for Cromwell server. DEFAULT \$SRC_DIR/cromwell.conf
--workflow-options   Local path to workflow_options.json. DEFAULT \$SRC_DIR/workflow_options.json
--machine-type       GCP machine type for the instance. DEFAULT e2-standard-2.
                     This flag is overridden if --custom-cpu and --custom-memory are specified.
                     Check gcloud documentations for further details.
--zone               DEFAULT us-central1-c. For options, visit: https://cloud.google.com/compute/docs/regions-zones 

Additional arguments are passed directly to gsutil compute instances
create command. For more information on those arguments, check that commands
help page with

    gcloud compute instances create --help

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
        --cromwell-conf*)
            if [ ! "$2" ]; then
                CROMWELL_CONF="$SRC_DIR/cromwell.conf"
            else
                CROMWELL_CONF=$2
                shift
            fi
            ;;
	 --workflow-dir*)
            if [ ! "$2" ]; then
                WORKFLOW_OPTIONS="$SRC_DIR/workflow_options.json"
            else
                WORKFLOW_OPTIONS=$2
                shift
            fi
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
        --zone*)
            if [ ! "$2" ]; then
		ZONE="us-central1-c"
            else
                ZONE=$2
                shift
            fi
            ;;
        --custom-cpu*)
            if [ ! "$2" ]; then
                die 'ERROR: "--custom-cpu" requires an argument'
            else
                CPU=$2
                shift
            fi
            ;;
        --custom-memory*)
            if [ ! "$2" ]; then
                die 'ERROR: "--custom-memory" requires an argument'
            else
                MEM=$2
                shift
            fi
            ;;
        *)
            break
            ;;
    esac
    shift
done

[ -z $SERVER_ACCOUNT   ] && die "Missing argument --server-account"
[ -z $PROJECT          ] && die "Missing argument --project"
[ -z $CROMWELL_CONF    ] && CROMWELL_CONF="$SRC_DIR/cromwell.conf"
[ -z $WORKFLOW_OPTIONS ] && WORKFLOW_OPTIONS="$SRC_DIR/workflow_options.json"
[ -z $ZONE             ] && ZONE="us-central1-c"

if [[ ! -f $CROMWELL_CONF ]]; then
    cat <<EOF
cromwell.conf does not exist. Check passed value or generate via

    sh resources.sh generate-config --project PROJECT --bucket BUCKET

EOF
    exit 1
fi

if [[ ! -f $WORKFLOW_OPTIONS ]]; then
    cat <<EOF
workflow_options.json does not exist. Check passed value or generate via

    sh resources.sh generate-config --project PROJECT --bucket BUCKET

EOF
    exit 1
fi

MACHINE_TYPE=${MACHINE_TYPE:-"e2-standard-2"}

param=(
  --project $PROJECT
  --image-family debian-11
  --image-project debian-cloud
  --zone $ZONE
  --service-account=$SERVER_ACCOUNT
  --scopes=cloud-platform
  --network=$NETWORK
  --subnet=$SUBNET
  --metadata=cromwell-version=71
  --metadata-from-file=startup-script=$SRC_DIR/server_startup.py,cromwell-conf=$CROMWELL_CONF,helpers-sh=$SRC_DIR/helpers.sh,cromwell-service=$SRC_DIR/cromwell.service,workflow-options=$WORKFLOW_OPTIONS,persist-artifacts=$SRC_DIR/../scripts/persist_artifacts.py
)

# add machine type unless --custom-memory and --custom-cpu are specified
if [ -z "$MEM" ] || [ -z "$CPU" ]; then
  param+=(--machine-type=$MACHINE_TYPE)
else
  param+=(--custom-memory $MEM)
  param+=(--custom-cpu $CPU)
fi

# $@ indicates the ability to add any of the other flags that come with gcloud compute instances creat
# for a full account, visit https://cloud.google.com/sdk/gcloud/reference/compute/instances/create
gcloud compute instances create $INSTANCE_NAME \
       ${param[@]} \
       $@

cat <<EOF
To use this instance, SSH into it via:

    gcloud compute ssh $INSTANCE_NAME

To delete the instance when you're done:

    gcloud compute instances delete $INSTANCE_NAME

EOF
exit 0
