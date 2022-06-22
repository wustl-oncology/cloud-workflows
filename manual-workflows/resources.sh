#!/bin/bash

SRC_DIR=$(dirname "$0")

function show_help {
    echo "$0 - Create/Destroy resources for manual Cromwell workflow execution"
    echo ""
    echo "usage: sh $0 COMMAND --project <PROJECT> --bucket <BUCKET> --ip-range <RANGE>"
    echo ""
    echo "commands:"
    echo "    init-project        Create required resources for the project. You'll almost always want this one."
    echo "    generate-config     Generate the cromwell.conf file required by the VM"
    echo "                        Use this when project init'd but no local copy"
    echo ""
    echo "arguments:"
    echo "    -h, --help     print this block"
    echo "    --config-dir   a dir path that is writable, DEFAULT='\$SRC_DIR'"
    echo "    --bucket       name for the GCS bucket used by Cromwell"
    echo "    --project      name of your GCP project"
    echo "    --ip-range     block/range of acceptable IPs e.g. 172.16.0.0/24 or a single IP address e.g. 172.16.5.9/32 or a comma-seperated list of IPs/CIDRs."
    echo "    --gc-region    DEFAULT='us-central1'. For other regions check: https://cloud.google.com/compute/docs/regions-zones" 
    echo ""
}

# die and opts based on this example
# http://mywiki.wooledge.org/BashFAQ/035
# --long-opt* example here
# https://stackoverflow.com/a/7069755
function die {
    printf '%s\n' "$1" >&2 && exit 1
}

COMMAND=$1; shift
if [[ ($COMMAND != "init-project") && ($COMMAND != "generate-config")]]; then
    show_help
    die "ERROR: invalid command - $COMMAND"
fi

while test $# -gt 0; do
    case $1 in
        -h|--help)
            show_help
            exit
            ;;
        --config-dir*)
            if [ ! "$2" ]; then
                CONFIG_DIR=$SRC_DIR
            else
                CONFIG_DIR=$2
                shift
            fi
            ;;
        --bucket*)
            if [ ! "$2" ]; then
                die 'ERROR: "--bucket" requires a non-empty argument.'
            else
                BUCKET=$2
                shift
            fi
            ;;
        --project*)
            if [ ! "$2" ]; then
                die 'ERROR: "--project" requires a non-empty argument.'
            else
                PROJECT=$2
                shift
            fi
            ;;
	--ip-range*)
	    if [ ! "$2" ]; then
		die 'ERROR: "--ip-range" requires a non-empty argument.'
	    else
		IP_RANGE=$2
		shift
	    fi
	    ;;
	--gc-region*)
	    if [ ! "$2" ]; then
		GC_REGION="us-central1"
	    else
		GC_REGION=$2
		shift
	    fi
       	    ;;
        *)
            break
            ;;
    esac
    shift
done

if [ -z $CONFIG_DIR ]; then
    CONFIG_DIR=$SRC_DIR
fi
if [ -z $PROJECT ]; then
    die 'ERROR: "--project" must be set.'
fi
if [ -z $BUCKET ]; then
    die 'ERROR: "--bucket" must be set.'
fi
if [ -z $IP_RANGE ]; then
    die 'ERROR: "--ip-range" must be set.'
fi
if [ -z $GC_REGION ]; then
    GC_REGION="us-central1"
fi

COMPUTE_NAME="cromwell-compute"
SERVER_NAME="cromwell-server"
COMPUTE_ACCOUNT="$COMPUTE_NAME@$PROJECT.iam.gserviceaccount.com"
SERVER_ACCOUNT="$SERVER_NAME@$PROJECT.iam.gserviceaccount.com"

function generate_config {
    cp $SRC_DIR/base_cromwell.conf $CONFIG_DIR/cromwell.conf
    cat << EOF >> $CONFIG_DIR/cromwell.conf
backend.providers.default.config {
    project = "$PROJECT"
    root = "gs://$BUCKET/cromwell-executions"
    genomics.compute-service-account = "$COMPUTE_ACCOUNT"
    filesystems.gcs.project = "$PROJECT"
}
EOF
    cat <<EOF > $CONFIG_DIR/workflow_options.json
{
    "default_runtime_attributes": {
        "preemptible": 1,
        "maxRetries": 2
    },
    "final_workflow_log_dir": "gs://$BUCKET/final-logs",
    "final_call_logs": "gs://$BUCKET/call-logs"
}
EOF
}

sh $SRC_DIR/../scripts/enable_api.sh

case $COMMAND in
    "init-project")
        # Create service accounts
        sh $SRC_DIR/../scripts/create_resources.sh $PROJECT $SERVER_NAME $COMPUTE_NAME $BUCKET $IP_RANGE $GC_REGION
        # Create bucket if not exists
        # Generate cromwell.conf
        generate_config
        ;;
    "generate-config")
        generate_config
        ;;
esac

cat <<EOF

Completed $COMMAND. Check stderr logs and make sure nothing unexpected
happened. Script optimistically executes and will relay gcloud's error on
redundant operations, e.g. creating a resource that already exists.

    Service Account: $SERVER_ACCOUNT

EOF
