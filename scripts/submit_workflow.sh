#!/bin/bash

set -eo pipefail

CROMWELL_URL=${CROMWELL_URL:-'http://35.188.155.31:8000'}
function show_help {
    echo "$0 - submit Analysis Workflow WDLs to Cromwell server"
    echo ""
    echo "usage: $0 [options] <definition-wdl> <inputs-file>"
    echo ""
    echo "options:"
    echo "-h, --help                  print this block"
    echo "-w, --wdl-dir <DIR>         local dir of the analysis-wdls repo"
    echo "-c, --cromwell-url <URL>    URL of the server [default $CROMWELL_URL]"
    echo "--options <FILE>            workflow options json"
    exit 0
}

# die and opts based on this example
# http://mywiki.wooledge.org/BashFAQ/035
# --long-opt* example here
# https://stackoverflow.com/a/7069755
function die {
    printf '%s\n' "$1" >&2
}

while test $# -gt 0; do
    case $1 in
        -h|-\?|--help)
            show_help
            exit
            ;;
        -w|--wdl-dir*)
            if [ ! "$2" ] || [[ ! -d $2 ]]; then
                die 'ERROR: "--wdl-dir" requires an existing directory option argument.'
            else
                ANALYSIS_WDLS=$2
                shift
            fi
            ;;
        -c|--cromwell-url*)
            if [ ! "$2" ]; then
                die 'ERROR: "--cromwell-url" requires a non-empty option argument.'
            else
                CROMWELL_URL=$2
                shift
            fi
            ;;
        --options)
            if [ ! "$2" ] || [[ ! -f $2 ]]; then
                die 'ERROR: "--options" requires an existing file.'
            else
                WORKFLOW_OPTIONS=$2
                shift
            fi
            ;;
        *)
            break
    esac
    shift
done

# +--------------------+
# | Configuration vars |
# +--------------------+

WORKFLOW_DEFINITION=$1
WORKFLOW_INPUTS=$2

# derived
SRC_DIR="$(dirname "${BASH_SOURCE[0]}")"
WORKFLOW_OPTIONS=$SRC_DIR/workflow_options.json

# +---------------------+
# | ZIP dependencies    |
# +---------------------+

ZIP=$ANALYSIS_WDLS/workflows.zip
if [ -e ${ZIP} ]; then
    echo "Nuking out old dependency zip: ${ZIP}"; rm ${ZIP}
fi
OLD_DIR=$PWD; cd $ANALYSIS_WDLS/definitions/
zip -r $ZIP . 1> /dev/null
cd $OLD_DIR

# +---------------------+
# | Submitting workflow |
# +---------------------+
cat $WORKFLOW_OPTIONS
set -o xtrace

curl "$CROMWELL_URL/api/workflows/v1" \
     -F workflowSource=@${WORKFLOW_DEFINITION} \
     -F workflowInputs=@${WORKFLOW_INPUTS} \
     -F workflowDependencies=@${ZIP} \
     -F workflowOptions=@${WORKFLOW_OPTIONS}
set +o xtrace
