export CROMWELL_JAR=/opt/cromwell/jar/cromwell.jar
export CROMWELL_CONF=/opt/cromwell/config/cromwell.conf
export ANALYSIS_WDLS=/shared/analysis-wdls

function cromwell () {
    java -Dconfig.file=/shared/cromwell.conf -jar /shared/cromwell.jar $@
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
        echo "Usage: save_timing_chart WORKFLOW_ID GCS_PATH"
    else
        # Server start-up and destruction
        cromwell server > cromwell.log & > /dev/null
        CROMWELL_PID=$!

        echo "Instantiating cromwell server on pid [$CROMWELL_PID]"
        RESULT=$(( tail -f cromwell.log & ) | grep -oh -m 1 'service started\|Shutting down')
        if [[ $RESULT = "Shutting down" ]]; then
            echo "Cromwell failed to instantiate. View error logs at cromwell.log"
            kill  $CROMWELL_PID $(pgrep -P $CROMWELL_PID)
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
            kill $CROMWELL_PID $(pgrep -P $CROMWELL_PID)
        fi
    fi
}
