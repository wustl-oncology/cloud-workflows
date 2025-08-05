#!/bin/bash

# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# Script to submit jobs for single or multiple samples to run the immuno pipeline on storage1 using bsub
# Usage: bash run_immuno_compute1.sh --sample "Hu_254" --scratch_dir "/scratch1/fs1/mgriffit/jyao/miller_immuno" --job_group "/j.x.yao/2_job"
# Usage for multiple samples: bash run_immuno_compute1.sh --sample "Hu_344 Hu_048" --scratch_dir "/scratch1/fs1/mgriffit/jyao/miller_immuno" --job_group "/j.x.yao/2_job"

# Function to display usage
usage() {
    echo "Usage: $0 --sample <sample_id(s)> --scratch_dir <scratch_directory> --job_group <job_group>"
    echo "  --sample: Single sample ID (e.g., 'Hu_254') or multiple sample IDs (e.g., 'Hu_344 Hu_048')"
    echo "  --scratch_dir: Scratch directory to save pipeline artifacts"
    echo "  --job_group: Your LSF job group"
    echo ""
    echo "Examples:"
    echo "  $0 --sample 'Hu_254' --scratch_dir '/scratch1/fs1/mgriffit/jyao/miller_immuno' --job_group '/j.x.yao/2_job'"
    echo "  $0 --sample 'Hu_344 Hu_048' --scratch_dir '/scratch1/fs1/mgriffit/jyao/miller_immuno' --job_group '/j.x.yao/2_job'"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --sample)
            SAMPLES_STR="$2"
            shift 2
            ;;
        --scratch_dir)
            SCRATCH_DIR="$2"
            shift 2
            ;;
        --job_group)
            JOB_GROUP="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Check if all required arguments are provided
if [[ -z "$SAMPLES_STR" || -z "$SCRATCH_DIR" || -z "$JOB_GROUP" ]]; then
    echo "Error: Missing required arguments"
    usage
fi

# Convert sample string to array, work for a single sample or multiple samples
SAMPLES=($SAMPLES_STR)

# ----------------------------------------------------------------------------------------------------------------------------------------------------------
# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Set WORK_DIR to two levels up from the script's directory
WORK_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)" # change this to absolute path

# Create directory to store final outputs
OUT_DIR="$WORK_DIR/immuno_outputs"
# Check if OUT_DIR exists, if not, create it
[ -d "$OUT_DIR" ] || mkdir -p "$OUT_DIR"

# Directory to keep log files
LOG_DIR="$WORK_DIR/logs"
# Check if LOG_DIR exists, if not, create it
[ -d "$LOG_DIR" ] || mkdir -p "$LOG_DIR"

# ----------------------------------------------------------------------------------------------------------------------------------------------------------
# VALIDATION CHECKS - Run before processing any samples
echo "=== VALIDATION CHECKS ==="

# Check if cromwell.config.wdl exists
CROMWELL_CONFIG="$WORK_DIR/cloud-workflows/manual-workflows/cromwell.config.wdl"
if [[ ! -f "$CROMWELL_CONFIG" ]]; then
    echo "ERROR: Cromwell config file not found at: $CROMWELL_CONFIG"
    exit 1
fi

# Check if the default job group path exists in cromwell.config.wdl
if grep -q "/path/to/your/job_group" "$CROMWELL_CONFIG"; then
    echo "ERROR: Please update the job group path in $CROMWELL_CONFIG"
    echo "       Replace '/path/to/your/job_group' with your actual job group path"
    echo "       Current job group being used: $JOB_GROUP"
    exit 1
else
    echo "✓ Cromwell config file validated - job group path has been updated"
fi

# Check if all sample YAML files exist
echo "Checking for sample YAML files..."
MISSING_YAMLS=()
for SAMPLE in "${SAMPLES[@]}"; do
    YAML_FILE="$WORK_DIR/yamls/${SAMPLE}_immuno.yaml"
    if [[ ! -f "$YAML_FILE" ]]; then
        MISSING_YAMLS+=("$YAML_FILE")
    fi
done

if [[ ${#MISSING_YAMLS[@]} -gt 0 ]]; then
    echo "ERROR: Missing YAML files for the following samples:"
    for yaml in "${MISSING_YAMLS[@]}"; do
        echo "  - $yaml"
    done
    echo "Please run the YAML generation script first: bash run_make_input_yaml.sh"
    exit 1
else
    echo "✓ All sample YAML files found"
fi

# Check if scratch directory exists and is writable
if [[ ! -d "$SCRATCH_DIR" ]]; then
    echo "ERROR: Scratch directory does not exist: $SCRATCH_DIR"
    exit 1
fi

if [[ ! -w "$SCRATCH_DIR" ]]; then
    echo "ERROR: Scratch directory is not writable: $SCRATCH_DIR"
    exit 1
fi

echo "✓ Scratch directory validated"

# Check if analysis-wdls directory exists
if [[ ! -d "$WORK_DIR/analysis-wdls" ]]; then
    echo "ERROR: analysis-wdls directory not found at: $WORK_DIR/analysis-wdls"
    exit 1
fi

echo "✓ All validation checks passed"
echo ""

# ----------------------------------------------------------------------------------------------------------------------------------------------------------
# PREPARE WORKFLOWS
echo "=== PREPARING WORKFLOWS ==="

# Check if analysis-wdls/workflows.zip exists, and create it if not
cd "$WORK_DIR/analysis-wdls"
# Ensure workflows.zip file is up to date
# Ensure zip_wdls.sh is executable
chmod +x zip_wdls.sh
# Run the script to create workflows.zip
echo "Creating/updating workflows.zip..."
bash zip_wdls.sh

# Return to the original working directory
cd "$WORK_DIR"

echo "✓ Workflows prepared"
echo ""

# ----------------------------------------------------------------------------------------------------------------------------------------------------------
# RUN IMMUNO WORKFLOW
echo "=== SUBMITTING JOBS ==="
echo "Processing ${#SAMPLES[@]} sample(s): ${SAMPLES[*]}"
echo ""

# Loop through each sample and submit a job
for SAMPLE in "${SAMPLES[@]}"; do
    echo "Processing sample: $SAMPLE"
    
    # Define the sample-specific run directory
    RUN_DIR="$SCRATCH_DIR/$SAMPLE"
    
    # Create the directory if it does not exist
    if ! [ -e "$RUN_DIR" ]; then
        mkdir -p "$RUN_DIR"
        echo "  Created run directory: $RUN_DIR"
    fi

    # Navigate to the run directory
    cd "$RUN_DIR"

    # Create a detailed log file for this sample
    SAMPLE_LOG="$LOG_DIR/${SAMPLE}_detailed.log"
    {
        echo "=== SAMPLE PROCESSING LOG ==="
        echo "Sample Name: $SAMPLE"
        echo "Working Directory: $WORK_DIR"
        echo "Output Directory: $OUT_DIR/${SAMPLE}_out"
        echo "Log Directory: $LOG_DIR"
        echo "Run Directory: $RUN_DIR"
        echo "Job Group: $JOB_GROUP"
        echo "Timestamp: $(date)"
        echo ""
        echo "Job submission command:"
        echo "bsub -q oncology -G compute-oncology -g \"$JOB_GROUP\" -M 22000000 \\"
        echo "     -R 'select[mem>22000] rusage[mem=22000]' -J \"$SAMPLE\" \\"
        echo "     -oo \"$LOG_DIR/$SAMPLE.stdout\" \\"
        echo "     -a 'docker(ghcr.io/genome/genome_perl_environment:compute1-58)' \\"
        echo "     /bin/bash \"$WORK_DIR/cloud-workflows/manual-workflows/runCromwellWDL.sh\" \\"
        echo "     --workflow_dir \"$WORK_DIR/cloud-workflows\" \\"
        echo "     --cromwell_config \"$WORK_DIR/cloud-workflows/manual-workflows/cromwell.config.wdl\" \\"
        echo "     --sample $SAMPLE \\"
        echo "     --wdl \"$WORK_DIR/analysis-wdls/definitions/immuno.wdl\" \\"
        echo "     --imports \"$WORK_DIR/analysis-wdls/workflows.zip\" \\"
        echo "     --yaml \"$WORK_DIR/yamls/${SAMPLE}_immuno.yaml\" \\"
        echo "     --results \"$OUT_DIR/${SAMPLE}_out\" \\"
        echo "     --temp $RUN_DIR \\"
        echo "     --cromwell_jar \"/storage1/fs1/mgriffit/Active/griffithlab/common/cromwell-jars/cromwell-71.jar\" \\"
        echo "     --cromwell_server_mem 10g --cromwell_submit_mem 10g --clean YES"
        echo ""
    } > "$SAMPLE_LOG"

    # Submit the job using bsub
    echo "  Submitting job for $SAMPLE..."
    bsub -q oncology -G compute-oncology -g "$JOB_GROUP" -M 22000000 \
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

    # Check if job submission was successful
    if [[ $? -eq 0 ]]; then
        echo "  ✓ Job submitted successfully for $SAMPLE"
        echo "  ✓ Detailed log saved to: $SAMPLE_LOG"
    else
        echo "  ✗ Failed to submit job for $SAMPLE"
        exit 1
    fi

    # Create a script with the bsub command
    TEMP_SCRIPT="$RUN_DIR/runWDL_$SAMPLE.sh"
cat <<EOT > "$TEMP_SCRIPT"
        #!/bin/bash
    bsub -q oncology -G compute-oncology -g "$JOB_GROUP" -M 22000000 \
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
    echo ""
done

echo "=== JOB SUBMISSION COMPLETE ==="
echo "All jobs have been submitted successfully!"
echo ""
echo "Summary:"
echo "  - Samples being processed: ${SAMPLES[*]}"
echo "  - Output directory: $OUT_DIR"
echo "  - Log directory: $LOG_DIR"
echo "  - Scratch directory: $SCRATCH_DIR"
echo ""
echo "To monitor your jobs, use:"
echo "  bjobs -g $JOB_GROUP"
echo ""
echo "To check other sub-jobs"
echo "  bjobs"
