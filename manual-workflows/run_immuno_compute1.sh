#!/bin/bash

# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# Script to submit jobs for single or multiple samples to run the immuno pipeline on storage1 using bsub
# Usage: bash run_immuno_compute1.sh "Hu_250" "/scratch1/fs1/mgriffit/jyao/miller_immuno/" "/j.x.yao/2_job"

# Sample IDs to process
SAMPLES=($1)  # e.g. "Hu_250" or "Hu_250 Hu_048"
# Scratch directory to save pipeline artifacts
SCRATCH_DIR=$2
# Your LSF job group here
JOB_GROUP=$3

# ----------------------------------------------------------------------------------------------------------------------------------------------------------

# List of samples IDs to process
# Run multiplt samples 
#SAMPLES=("M221" "M222" "M223" "M225" "M228")
# Run one sample
#SAMPLES=("Hu_250") # <-- change this to your own sample IDs

# Scratch directory to save pipeline artifacts
#SCRATCH_DIR="/scratch1/fs1/mgriffit/jyao/miller_immuno/" # <-- change this to your own scratch directory

# Set your LSF job group here
#JOB_GROUP="/j.x.yao/2_job" # <-- change this to your own job group


# Define the working directory and the script to be executed
WORK_DIR="../.."

# Create directory to store final outputs
OUT_DIR="$WORK_DIR/immuno_outputs"
# Check if OUT_DIR exists, if not, create it
[ -d "$OUT_DIR" ] || mkdir -p "$OUT_DIR"

# Directory to keep log files
LOG_DIR="$WORK_DIR/logs"
# Check if LOG_DIR exists, if not, create it
[ -d "$LOG_DIR" ] || mkdir -p "$LOG_DIR"


# Check if analysis-wdls/workflows.zip exists, and create it if not
cd "$WORK_DIR/analysis-wdls"

if [ ! -f "workflows.zip" ]; then
    # Ensure zip_wdls.sh is executable
    chmod +x zip_wdls.sh
    # Run the script to create workflows.zip
    bash zip_wdls.sh
fi

# Return to the original working directory
cd "$WORK_DIR"



# Run immuno workflow ------------------------------------------------------------------------------
# Loop through each sample and submit a job
for SAMPLE in "${SAMPLES[@]}"; do
    # Define the sample-specific run directory
    RUN_DIR="$SCRATCH_DIR/$SAMPLE"
    
    # Create the directory if it does not exist
    if ! [ -e "$RUN_DIR" ]; then
        mkdir -p "$RUN_DIR"
    fi

    # Navigate to the run directory
    cd "$RUN_DIR"

    # Submit the job using bsub
    bsub -q general -G compute-oncology -g "$JOB_GROUP" -M 22000000 \
         -R 'select[mem>22000] rusage[mem=22000]' -J "$SAMPLE" \
         -oo "$LOG_DIR/$SAMPLE.stdout" \
         -a 'docker(ghcr.io/genome/genome_perl_environment:compute1-58)' \
         /bin/bash "$WORK_DIR/cloud-workflows/manual-workflows/runCromwellWDL.sh" \
         --workflow_dir "$WORK_DIR/cloud-workflows" \
         --cromwell_config "$WORK_DIR/cloud-workflows/manual-workflows/cromwell.config.wdl" \
         --sample $SAMPLE \
         --wdl "$WORK_DIR/analysis-wdls/definitions/immuno.wdl" \
         --imports "$WORK_DIR/analysis-wdls/workflows.zip" \
         --yaml "$WORK_DIR/yamls/${SAMPLE}_immuno.yaml" \
         --results "$OUT_DIR/${SAMPLE}_out" \
	 --temp $RUN_DIR \
         --cromwell_jar "/storage1/fs1/mgriffit/Active/griffithlab/common/cromwell-jars/cromwell-71.jar" \
         --cromwell_server_mem 10g --cromwell_submit_mem 10g --clean YES

    # Create a script with the bsub command
    TEMP_SCRIPT="$RUN_DIR/runWDL_$SAMPLE.sh"
cat <<EOT > "$TEMP_SCRIPT"
        #!/bin/bash
    bsub -q general -G compute-oncology -g "$JOB_GROUP" -M 22000000 \
         -R 'select[mem>22000] rusage[mem=22000]' -J "$SAMPLE" \
         -oo "$LOG_DIR/$SAMPLE.stdout" \
         -a 'docker(ghcr.io/genome/genome_perl_environment:compute1-58)' \
         /bin/bash $WORK_DIR/cloud-workflows/manual-workflows/runCromwellWDL.sh \
         --workflow_dir $WORK_DIR/cloud-workflows \
         --cromwell_config "$WORK_DIR/cloud-workflows/manual-workflows/cromwell.config.wdl" \
         --sample $SAMPLE \
         --wdl $WORK_DIR/analysis-wdls/definitions/immuno.wdl \
         --imports $WORK_DIR/analysis-wdls/workflows.zip \
         --yaml $WORK_DIR/yamls/${SAMPLE}_immuno.yaml \
         --results $OUT_DIR/${SAMPLE}_out \
         --cromwell_jar /storage1/fs1/mgriffit/Active/griffithlab/common/cromwell-jars/cromwell-71.jar \
         --cromwell_server_mem 10g --cromwell_submit_mem 10g -- clean YES
EOT
    
    # Navigate back to the working directory
    cd "$WORK_DIR"
done
