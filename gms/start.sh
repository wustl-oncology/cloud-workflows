#!/bin/bash

SRC_DIR="$(dirname "${BASH_SOURCE[0]}")"

CROMWELL_VERSION=71

function show-help {
    echo "$0 - Start a new Cromwell VM instance to run workflow"
    echo ""
    echo "usage: $0 [--argument value]*"
    echo ""
    echo "arguments:"
    echo "-h, --help             print this block and immediately exits"
    echo "--build                Used to distinguish resources in a shared project"
    echo "                       Assumes only one cloud run per build at a time"
    echo "--bucket               Name of the GCS bucket to store artifacts like timing diagram"
    echo "--deps-zip             GCS path to WDL dependencies in a .zip file"
    echo "--service-account      Email identifier of service account used by main Cromwell instance"
    echo "--cromwell-conf        Local path to configuration file for Cromwell server"
    echo "--workflow-definition  Local path to workflow definition .wdl file"
    echo "--workflow-inputs      Local path to workflow inputs .yaml file"
    echo "--workflow-options     Local path to workflow options .json file"
    echo ""
    echo "All arguments (besides help) are required and have an associated value. None are flags."
}


# die and opts based on this example
# http://mywiki.wooledge.org/BashFAQ/035
# --long-opt* example here
# https://stackoverflow.com/a/7069755
function die {
    printf '%s\n' "$1" >&2
    show-help
    exit 1
}

while test $# -gt 0; do
    case $1 in
        -h|-\?|--help)
            show-help
            exit 0
            ;;
        --workflow-definition*)
            if [ -e $2 ]; then
                WORKFLOW_DEFINITION=$2
                shift
            else
                die 'ERROR: "--workflow-definition" requires an existing file argument.'
            fi
            ;;
        --workflow-inputs*)
            if [[ ! -e $2 ]]; then
                die 'ERROR: "--workflow-inputs" requires an existing file argument.'
            else
                WORKFLOW_INPUTS=$2
                shift
            fi
            ;;
        --workflow-options*)
            if [[ ! -e $2 ]]; then
                die 'ERROR: "--workflow-options" requires an existing file argument.'
            else
                WORKFLOW_OPTIONS=$2
                shift
            fi
            ;;
        --service-account*)
            if [ ! "$2" ]; then
                die 'ERROR: "--service-account" requires an email argument.'
            else
                SERVICE_ACCOUNT=$2
                shift
            fi
            ;;
        --deps-zip*)
            if [ ! "$2" ]; then
                die 'ERROR: "--deps-zip" requires an existing file argument.'
            else
                DEPS_ZIP=$2
                shift
            fi
            ;;
        --build*)
            if [ ! "$2" ]; then
                die 'ERROR: "--build" requires a uuid argument.'
            else
                BUILD=$2
                shift
            fi
            ;;
        --bucket*)
            if [ ! "$2" ]; then
                die 'ERROR: "--bucket" requires a string for the name of your bucket.'
            else
                BUCKET=$2
                shift
            fi
            ;;
        --cromwell-conf*)
            if [[ ! -e $2 ]]; then
                die 'ERROR: "--cromwell-conf" requires an existing file argument.'
            else
                CROMWELL_CONF=$2
                shift
            fi
            ;;
    esac
    shift
done

[ -z $BUCKET ] && die "Missing --bucket argument."
[ -z $BUILD ] && die "Missing --build argument."
[ -z $CROMWELL_CONF ] && die "Missing --cromwell-conf argument."
[ -z $DEPS_ZIP ] && die "Missing --deps-zip argument."
[ -z $SERVICE_ACCOUNT ] && die "Missing --service-account argument."
[ -z $WORKFLOW_DEFINITION ] && die "Missing --workflow-definition argument."
[ -z $WORKFLOW_INPUTS ] && die "Missing --workflow-inputs argument."
[ -z $WORKFLOW_OPTIONS ] && die "Missing --workflow-options argument."

gcloud compute instances create $BUILD \
       --image-family debian-11 \
       --image-project debian-cloud \
       --zone us-central1-c \
       --network=default --subnet=default \
       --scopes=cloud-platform \
       --service-account=$SERVICE_ACCOUNT \
       --metadata=cromwell-version=$CROMWELL_VERSION,deps-zip=$DEPS_ZIP,bucket=$BUCKET,build-id=$BUILD,auto-shutdown=1 \
       --metadata-from-file=startup-script=$SRC_DIR/server_startup.py,cromwell-conf=$CROMWELL_CONF,cromwell-service=$SRC_DIR/cromwell.service,workflow-wdl=$WORKFLOW_DEFINITION,inputs-yaml=$WORKFLOW_INPUTS,options-json=$WORKFLOW_OPTIONS
