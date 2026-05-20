#!/bin/bash

# EXAMPLE COMMAND:
#sbatch --mem=22G -p short \
#-o /path/to/output/dir/sample.stdout \
#-e /path/to/output/dir/sample.stderr \
#--wrap "/bin/bash /path/to/cloud-workflows/manual-workflows/runCromwellWDL_slurm.sh \
#-d /absolute/path/to/cloud-workflows \
#--cromwell_config /path/to/cromwell.conf \
#--sample MySample \
#--wdl /path/to/analysis-wdls/definitions/immuno.wdl \
#--imports /path/to/analysis-wdls/workflows.zip \
#--yaml /path/to/inputs.json \
#--results /path/to/final_results \
#--temp /path/to/scratch/tmp \
#--cromwell_server_mem 10g \
#--cromwell_submit_mem 10g"

#NOTE. When specifying memory for the two Java commands below (which run in parallel) make sure they add up to LESS than what is requested for the parent SLURM job.
function usage
{
    echo ""
    echo "usage: runCromwellWDL_slurm.sh -d <cloud-workflows-path> -h"
    echo ""
    echo "  -d | --workflow_dir          Path to cloud-workflows directory (required)"
    echo "  -g | --cromwell_config       Path to cromwell config file"
    echo "  -s | --sample                Sample name"
    echo "  -w | --wdl                   Path to WDL pipeline file"
    echo "  -i | --imports               Path to ZIP archive of all WDL files"
    echo "  -y | --yaml                  Path to input YAML file"
    echo "  -r | --results               Path to final results dir where named outputs of the pipeline will be placed"
    echo "  -t | --temp                  Path to temp dir where intermediate pipeline files will be stored (e.g., scratch dir)"
    echo "  -a | --cromwell_server_mem   Memory (GB) used for the Java process for Cromwell Server command"
    echo "  -b | --cromwell_submit_mem   Memory (GB) used for the Java process for Cromwell Submit command"
    echo "  -k | --status_check_interval How long to wait before checking Cromwell for run status (default 600 seconds)"
    echo "  -n | --clean                 Whether to clean up or not (default: YES - things will be cleaned up unless you say --clean NO)"
    echo "  -c | --singularity_image     Singularity container image (default: docker://acoffman/cromwell-with-slurm:latest)"
    echo "  -e | --bind_paths            Additional comma-separated bind paths for singularity (optional)"
    echo "  -h | --help                  Show this message"
    echo ""
    exit 1
}

if [[ $1 == "" ]];then
    usage
    exit;
fi

# Parse arguments
while [[ "$1" != "" ]]; do
    case $1 in
         -d | --workflow_dir )           shift
                                         workflow_dir=$1
                                         ;;
         -g | --cromwell_config )        shift
                                         cromwell_config=$1
                                         ;;
         -s | --sample )                 shift
                                         sample=$1
                                         ;;
        -w | --wdl )                     shift
                                         wdl=$1
                                         ;;
        -i | --imports )                 shift
                                         imports=$1
                                         ;;
        -y | --yaml )                    shift
                                         yaml=$1
                                         ;;
        -t | --temp )                    shift
                                         temp=$1
                                         ;;
        -r | --results )                 shift
                                         results=$1
                                         ;;
        -a | --cromwell_server_mem )     shift
                                         cromwell_server_mem=$1
                                         ;;
        -b | --cromwell_submit_mem )     shift
                                         cromwell_submit_mem=$1
                                         ;;
        -k | --status_check_interval )   shift
                                         status_check_interval=$1
                                         ;;
        -n | --clean )                   shift
                                         clean=$1
                                         ;;
        -c | --singularity_image )       shift
                                         singularity_image=$1
                                         ;;
        -e | --bind_paths )              shift
                                         bind_paths=$1
                                         ;;
        -h | --help )                    usage
                                         exit
                                         ;;
        * )                              usage
                                         exit 1
    esac
    shift
done

if [[ $workflow_dir == "" ]];then
    echo "--workflow_dir must be specified (path to cloud-workflows repository)"
    exit;
fi
if [[ $cromwell_config == "" ]];then
    echo "--cromwell_config must be specified"
    exit;
fi
if [[ $sample == "" ]];then
    echo "--sample must be specified"
    exit;
fi
if [[ $wdl == "" ]];then
    echo "--wdl must be specified"
    exit;
fi
if [[ $imports == "" ]];then
    echo "--imports must be specified"
    exit;
fi
if [[ $yaml == "" ]];then
    echo "--yaml must be specified"
    exit;
fi
if [[ $results == "" ]];then
    echo "--results must be specified"
    exit;
fi
if [[ $temp == "" ]];then
    echo "--temp must be specified"
    exit;
fi
if [[ $cromwell_server_mem == "" ]];then
    echo "--cromwell_server_mem (in GB) must be specified (e.g. --cromwell_server_mem=10g)"
    exit;
fi
if [[ $cromwell_submit_mem == "" ]];then
    echo "--cromwell_submit_mem (in GB) must be specified (e.g. --cromwell_submit_mem=10g)"
    exit;
fi
if [[ $status_check_interval == "" ]];then
    echo "Interval used to check Cromwell for run status will be 600 seconds"
    status_check_interval="600"
fi
if [[ $clean == "" ]];then
    echo "Temp files will be cleaned up"
    clean="YES";
fi
if [[ $singularity_image == "" ]];then
    singularity_image="docker://acoffman/cromwell-with-slurm:latest"
    echo "Using default singularity image: $singularity_image"
fi

###########################################################################################
############################# pre-setup ###################################################
###########################################################################################

# Ensure host-side curl talks directly to the in-container Cromwell server on
# loopback rather than routing through the cluster's HTTP proxy (which denies
# loopback connections).
export no_proxy="localhost,127.0.0.1${no_proxy:+,$no_proxy}"
export NO_PROXY="$no_proxy"
echo "no_proxy set to: $no_proxy"

JAVA_MEM_BASE="-Xmx"
CROMWELL_SERVER_MEM_STRING="$JAVA_MEM_BASE$cromwell_server_mem"
CROMWELL_SUBMIT_MEM_STRING="$JAVA_MEM_BASE$cromwell_submit_mem"
CROMWELL_JAR="/app/cromwell.jar"

echo "Java memory request for Server command: " $CROMWELL_SERVER_MEM_STRING
echo "Java memory request for Submit command: " $CROMWELL_SUBMIT_MEM_STRING
echo "Singularity image: " $singularity_image

###########################################################################################
##################### build singularity bind paths ########################################
###########################################################################################

# Start with the base bind paths required for SLURM/auth on the cluster
BIND_PATHS="/etc/passwd,/var/lib/sss/pipes,/run/munge,/cm/shared/apps/slurm/"

# Auto-append parent directories of input files so the container can access them
# Collect unique directories to avoid duplicate bind mounts
declare -A seen_dirs
for filepath in "$cromwell_config" "$wdl" "$imports" "$yaml" "$temp" "$results"; do
    if [[ -n "$filepath" ]]; then
        dir="$(dirname "$(readlink -f "$filepath" 2>/dev/null || echo "$filepath")")"
        if [[ -n "$dir" && -z "${seen_dirs[$dir]}" ]]; then
            seen_dirs[$dir]=1
            BIND_PATHS="$BIND_PATHS,$dir"
        fi
    fi
done

# Append any user-specified extra bind paths
if [[ -n "$bind_paths" ]]; then
    BIND_PATHS="$BIND_PATHS,$bind_paths"
fi

echo "Singularity bind paths: $BIND_PATHS"

###########################################################################################
###################start up the cromwell server/start job #################################
###########################################################################################

#create temp dir where cromwell will be run
if mkdir -p "$temp"; then
    echo "Successfully created: $temp"
else
    echo "Failed to create: $temp"
    exit 1
fi

# Attempt to change to the target directory
if cd "$temp"; then
    echo "Successfully changed to directory: $temp"
else
    echo "Failed to change directory to: $temp"
    exit 1
fi

# create a yaml to label the cromwell job
echo -e "{\n\"model\":\"$sample\"\n}" >| $sample.label

# start cromwell server and submit job inside a single singularity container
# this mirrors the original LSF script where both java processes share the same context
echo "Starting Cromwell server and submitting job inside singularity container..."
echo singularity exec --bind $BIND_PATHS $singularity_image /bin/bash
singularity exec --bind $BIND_PATHS $singularity_image /bin/bash -c "
    # start cromwell server and give it time to setup
    echo 'Starting Cromwell server...'
    java $CROMWELL_SERVER_MEM_STRING -Dconfig.file=$cromwell_config -jar $CROMWELL_JAR server &
    CROMWELL_SERVER_PID=\$!
    echo sleep 60
    sleep 60

    # submit the cromwell job
    echo 'Submitting workflow...'
    echo java $CROMWELL_SUBMIT_MEM_STRING -Dconfig.file=$cromwell_config -jar $CROMWELL_JAR submit -h http://127.0.0.1:8000 -l $sample.label -t wdl -i $yaml -p $imports $wdl
    java $CROMWELL_SUBMIT_MEM_STRING -Dconfig.file=$cromwell_config -jar $CROMWELL_JAR submit \
        -h http://127.0.0.1:8000 -l $sample.label -t wdl -i $yaml -p $imports $wdl

    # wait for the background server process to keep the container alive
    wait
" &
SINGULARITY_PID=$!
trap "kill $SINGULARITY_PID 2>/dev/null" EXIT

# wait for the server to be available on the host before proceeding to status polling
echo "Waiting for Cromwell server to become available..."
for i in $(seq 1 90); do
    if curl -fsS --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/engine/v1/status > /dev/null 2>&1; then
        echo "Cromwell server is ready"
        break
    fi
    if [ $i -eq 90 ]; then
        echo "Cromwell server failed to start within 7.5 minutes"
        exit 1
    fi
    sleep 5
done

############################################################################################
################# query the cromwell server for status #####################################
############################################################################################

# infinity loop to check job status
x=0
while [ $x -le 1 ]
do
    curl -fsSL --noproxy 127.0.0.1,localhost "http://127.0.0.1:8000/api/workflows/v1/query?label=model:${sample}" >| "$sample.status"
    sleep $status_check_interval
    if cat $sample.status | python3 -m json.tool | grep -q "Succeeded"; then
        break
    elif cat $sample.status | python3 -m json.tool | grep -q "Failed"; then
        exit 1
    else
        continue
    fi
done

############################################################################################
################ grab the final outputs and put them in the correct place ##################
############################################################################################

# with the cromwell job complete get the name and id so we can query and clean up the outputs
CROMWELL_ID="$(cat $sample.status | python3 -m json.tool | grep "\"id\":" | sed 's@.*\"id\": \"\(.*\)\".*@\1@')"
CROMWELL_NAME="$(cat $sample.status | python3 -m json.tool | grep "\"name\":" | sed 's@.*\"name\": \"\(.*\)\".*@\1@')"

# Set absolute path to scripts directory
SCRIPTS_DIR="$workflow_dir/scripts"

function save_artifacts () {
    WORKFLOW_ID=$1
    DESTINATION_PATH=$2
    if [[ -z $WORKFLOW_ID || -z $DESTINATION_PATH ]]; then
        echo "Usage: save_artifacts WORKFLOW_ID DESTINATION_PATH"
    elif ! curl -fsS --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/engine/v1/status > /dev/null 2>&1; then
        echo "Cromwell server does not appear to be running on localhost:8000. Cannot save artifacts."
    else
        if [[ ! -d $DESTINATION_PATH ]]; then
            echo "Directory $DESTINATION_PATH does not exist. Creating it..."
            mkdir -p $DESTINATION_PATH
        fi
        python3 "$SCRIPTS_DIR/persist_artifacts.py" $DESTINATION_PATH $WORKFLOW_ID
    fi
}
save_artifacts $CROMWELL_ID $results/workflow_artifacts/


# Define function to pull outputs (similar to save_artifacts)
function pull_outputs () {
    OUTPUTS_FILE=$1
    DESTINATION_PATH=$2
    if [[ -z $OUTPUTS_FILE || -z $DESTINATION_PATH ]]; then
        echo "Usage: pull_outs OUTPUTS_FILE DESTINATION_PATH"
    else
        if [[ ! -d $DESTINATION_PATH ]]; then
            echo "Directory $DESTINATION_PATH does not exist. Creating it..."
            mkdir -p $DESTINATION_PATH
        fi
        python3 "$SCRIPTS_DIR/pull_outputs.py" --outputs-file=$OUTPUTS_FILE --outputs-dir=$DESTINATION_PATH
    fi
}
pull_outputs $results/workflow_artifacts/outputs.json $results

#############################################################################################
################ with everything now done clean up after yourself ###########################
#############################################################################################

if [ $clean == "NO" ]; then
    echo "Leaving full cromwell-executions dir and temp files in place"
else
    echo "Removing cromwell-executions dir"
    echo rm -rf $temp/cromwell-executions/$CROMWELL_NAME/$CROMWELL_ID
    rm -rf $temp/cromwell-executions/$CROMWELL_NAME/$CROMWELL_ID

    echo rm -f $temp/$sample.final_results
    rm -f $temp/$sample.final_results

    echo rm -f $temp/$sample.output
    rm -f $temp/$sample.output

    echo rm -f $temp/$sample.status
    rm -f $temp/$sample.status

    echo rm -f $temp/$sample.label
    rm -f $temp/$sample.label
fi
