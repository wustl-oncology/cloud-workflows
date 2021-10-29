export CROMWELL_JAR=/opt/cromwell/jar/cromwell.jar
export CROMWELL_CONF=/opt/cromwell/config/cromwell.conf
export ANALYSIS_WDLS=/shared/analysis-wdls

function cat-startup-logs () {
    cat /var/log/syslog |  grep 'startup-script' | sed 's/ GCEMetadataScripts.*startup-script//'
}

function cromwell () {
    java -Dconfig.file=/opt/cromwell/config/cromwell.conf -jar /opt/cromwell/jar/cromwell.jar $@
}

function refresh_zip_deps () {
    rm /shared/analysis-wdls/workflows.zip
    OLD_DIR=$PWD; cd /shared/analysis-wdls/definitions/
    zip -r /shared/analysis-wdls/workflows.zip . 1> /dev/null
    cd $OLD_DIR
}

# TODO: add resiliency.  This assumes no issues (1) starting server
function save_timing_chart () {
    WORKFLOW_ID=$1
    GCS_PATH=$2
    if [[ -z $WORKFLOW_ID || -z $GCS_PATH ]]; then
        echo "Usage: save_timing_chart WORKFLOW_ID GCS_PATH"
    else
        # Server start-up and destruction
        cromwell server > cromwell.log &
        CROMWELL_PID=$!
        trap 'kill $CROMWELL_PID $(($CROMWELL_PID + 1)) $(($CROMWELL_PID + 2)) && echo KILLED_TRAP' EXIT

        echo "Started cromwell server on pid [$CROMWELL_PID]"
        ( tail -f cromwell.log & ) | grep -q 'service started on'
        echo "Cromwell server completed startup"
        curl --fail http://localhost:8000/api/workflows/v1/$WORKFLOW_ID/timing > ${WORKFLOW_ID}_timing.html || \
            echo "Request for timing diagram on workflow $WORKFLOW_ID failed."
        if [[ -s ${WORKFLOW_ID}_timing.html ]]; then
            gsutil cp $GCS_PATH ${WORKFLOW_ID}_timing.html
        fi
        kill $CROMWELL_PID $(($CROMWELL_PID + 1)) $(($CROMWELL_PID + 2))
    fi
}
