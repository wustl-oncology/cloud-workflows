#!/bin/bash

set -eo pipefail

if [[ $# -ne 2 || $1 == "--help" ]]; then
    echo "total args $#"
    echo "usage: $0 <workflow_definition> <inputs_yaml>"
    echo "Submit a genome/analysis-workflow to a running Cromwell server."
    echo ""
    echo "        --help\tshow this usage display"
    exit 1
fi


# +--------------------+
# | Configuration vars |
# +--------------------+

WORKFLOW_DEFINITION=${1:-$WORKFLOW_DEFINITION}
WORKFLOW_INPUTS=${2:-$WORKFLOW_INPUTS}

# may change per person
ANALYSIS_WORKFLOWS=$HOME/washu/analysis-workflows
ANALYSIS_WDLS=$HOME/washu/analysis-wdls
CROMWELL_URL=${CROMWELL_URL:-'http://35.188.155.31:8000'}

# derived
SRC_DIR="$(dirname "${BASH_SOURCE[0]}")"
WORKFLOW_OPTIONS=$SRC_DIR/workflow_options.json

# ------- zip stuff --------
function zip_analysis_workflows () {
    WF_DIR=$ANALYSIS_WORKFLOWS
    ZIP=$WF_DIR/zips/workflows.zip
    SRC_WFS=$WF_DIR/definitions/pipelines/
    if [ -e ${ZIP} ]; then
        echo "Nuking out old dependency zip: ${ZIP}"
        rm ${ZIP}
    fi
    # want to maintain the ../ prefix
    OLD_DIR=$PWD; cd $SRC_WFS
    zip -r $ZIP . .. 1> /dev/null
    cd $OLD_DIR
}

function zip_analysis_wdls () {
    WF_DIR=$ANALYSIS_WDLS
    ZIP=$WF_DIR/zips/workflows.zip
    SRC_WFS=$WF_DIR/definitions/
    if [ -e ${ZIP} ]; then
        echo "Nuking out old dependency zip: ${ZIP}"
        rm ${ZIP}
    fi
    # want to maintain the ../ prefix
    OLD_DIR=$PWD; cd $SRC_WFS
    zip -r $ZIP . 1> /dev/null
    cd $OLD_DIR
}

zip_analysis_wdls && ZIP=$ANALYSIS_WDLS/zips/workflows.zip


# +---------------------+
# | Submitting workflow |
# +---------------------+
cat $WORKFLOW_OPTIONS
set -o xtrace
curl -v "$CROMWELL_URL/api/workflows/v1" \
     -F workflowSource=@${WORKFLOW_DEFINITION} \
     -F workflowInputs=@${WORKFLOW_INPUTS} \
     -F workflowDependencies=@${ZIP} \
     -F workflowOptions=@${WORKFLOW_OPTIONS}
set +o xtrace
