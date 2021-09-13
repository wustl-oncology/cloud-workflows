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
if [[ ! -d $ANALYSIS_WDLS ]]; then
    echo "ANALYSIS_WDLS must be an existing directory. Current value: $ANALYSIS_WDLS"
    exit 1
fi

# +--------------------+
# | Configuration vars |
# +--------------------+

WORKFLOW_DEFINITION=$1
WORKFLOW_INPUTS=$2
CROMWELL_URL=${CROMWELL_URL:-'http://35.188.155.31:8000'}

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

curl -v "$CROMWELL_URL/api/workflows/v1" \
     -F workflowSource=@${WORKFLOW_DEFINITION} \
     -F workflowInputs=@${WORKFLOW_INPUTS} \
     -F workflowDependencies=@${ZIP} \
     -F workflowOptions=@${WORKFLOW_OPTIONS}
set +o xtrace
