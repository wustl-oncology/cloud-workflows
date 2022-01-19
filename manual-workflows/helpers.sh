#!/bin/bash

function submit_workflow () {
    WORKFLOW_DEFINITION=$1
    WORKFLOW_INPUTS=$2
    if [[ -z $1 || -z $2 ]]; then
        echo "Usage: submit_workflow WORKFLOW_DEFINITION WORKFLOW_INPUTS"
    else
        curl localhost:8000/api/workflows/v1 \
             -F workflowSource=@${WORKFLOW_DEFINITION} \
             -F workflowInputs=@${WORKFLOW_INPUTS} \
             -F workflowDependencies=@/shared/analysis-wdls/workflows.zip
    fi
}

function refresh_zip_deps () {
    rm /shared/analysis-wdls/workflows.zip
    OLD_DIR=$PWD; cd /shared/analysis-wdls/definitions/
    zip -r /shared/analysis-wdls/workflows.zip . 1> /dev/null
    cd $OLD_DIR
}

function save_artifacts () {
    WORKFLOW_ID=$1
    GCS_PATH=$2
    if [[ -z $WORKFLOW_ID || -z $GCS_PATH ]]; then
        echo "Usage: save_artifacts WORKFLOW_ID GCS_PATH"
    elif [[ $(systemctl is-active --quiet cromwell) -ne 0 ]]; then
        echo "Make sure Cromwell service is active before saving.\n\n    sudo systemctl start cromwell\n"
    else
        echo "Cromwell server completed startup"
        mkdir -p $WORKFLOW_ID
        curl --fail http://localhost:8000/api/workflows/v1/$WORKFLOW_ID/timing \
             > ${WORKFLOW_ID}/timing.html
        if [ $? -ne 0 ]; then
            echo "Request for timing diagram on workflow $WORKFLOW_ID failed."
        fi
        curl --fail http://localhost:8000/api/workflows/v1/$WORKFLOW_ID/outputs \
             > ${WORKFLOW_ID}/outputs.json
        if [ $? -ne 0 ]; then
            echo "Request for outputs on workflow $WORKFLOW_ID failed."
        fi
        gsutil cp -r ${WORKFLOW_ID} $GCS_PATH/${WORKFLOW_ID}
    fi
}
