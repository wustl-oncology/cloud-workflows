#!/bin/bash

SRC_DIR=$(dirname "$0")

CROMWELL_VERSION=71

show_help () {
    cat <<EOF
$0 - Start a new Cromwell VM instance to run workflow
usage: $0 [--argument value]*

arguments:
-h, --help             print this block and immediately exits
--build                Used to distinguish resources in a shared project
                       Assumes only one cloud run per build at a time
--bucket               Name of the GCS bucket to store artifacts like timing diagram
--deps-zip             GCS path to WDL dependencies in a .zip file
--service-account      Email identifier of service account used by main Cromwell instance
--cromwell-conf        Local path to configuration file for Cromwell server
--workflow-definition  Local path to workflow definition .wdl file
--workflow-inputs      Local path to workflow inputs .yaml file
--workflow-options     Local path to workflow options .json file

All arguments (besides help) are required and have an associated value. None are flags.
EOF
}


# die and opts based on this example
# http://mywiki.wooledge.org/BashFAQ/035
# --long-opt* example here
# https://stackoverflow.com/a/7069755
die () {
    printf '%s\n\n' "$1" >&2
    show_help
    exit 1
}

while test $# -gt 0; do
    case $1 in
        -h|-\?|--help)
            show_help
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
            if [ ! -e $2 ]; then
                die 'ERROR: "--workflow-inputs" requires an existing file argument.'
            else
                WORKFLOW_INPUTS=$2
                shift
            fi
            ;;
        --workflow-options*)
            if [ ! -e $2 ]; then
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
            if [ ! -e $2 ]; then
                die 'ERROR: "--cromwell-conf" requires an existing file argument.'
            else
                CROMWELL_CONF=$2
                shift
            fi
            ;;
    esac
    shift
done

[ -z $BUCKET              ] && die "Missing argument --bucket"
[ -z $BUILD               ] && die "Missing argument --build"
[ -z $CROMWELL_CONF       ] && die "Missing argument --cromwell-conf"
[ -z $DEPS_ZIP            ] && die "Missing argument --deps-zip"
[ -z $SERVICE_ACCOUNT     ] && die "Missing argument --service-account"
[ -z $WORKFLOW_DEFINITION ] && die "Missing argument --workflow-definition"
[ -z $WORKFLOW_INPUTS     ] && die "Missing argument --workflow-inputs"
[ -z $WORKFLOW_OPTIONS    ] && die "Missing argument --workflow-options"

gcloud compute instances create $BUILD \
       --image-family debian-11 \
       --image-project debian-cloud \
       --zone us-central1-c \
       --network=default --subnet=default \
       --scopes=cloud-platform \
       --service-account=$SERVICE_ACCOUNT \
       --metadata=cromwell-version=$CROMWELL_VERSION,deps-zip=$DEPS_ZIP,bucket=$BUCKET,build-id=$BUILD,auto-shutdown=1 \
       --metadata-from-file=startup-script=$SRC_DIR/server_startup.py,cromwell-conf=$CROMWELL_CONF,cromwell-service=$SRC_DIR/cromwell.service,workflow-wdl=$WORKFLOW_DEFINITION,inputs-yaml=$WORKFLOW_INPUTS,options-json=$WORKFLOW_OPTIONS
