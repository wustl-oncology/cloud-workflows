#!/bin/bash

# Run-specific vars
WORKFLOW_CWL=${HOME}/analysis-workflows/definitions/pipelines/rnaseq.cwl
INPUTS_YAML=${HOME}/human_rna_qc_and_abundance/inputs.yaml
JOB_NAME=johnmaruska-gcs-upload

# Person-specific vars
EMAIL=john.maruska@wustl.edu
GROUP=compute-oncology
GCS_BUCKET=griffith-lab-cromwell
LSF_DOCKER_VOLUMES='/home/maruska:/home/maruska /storage1/fs1/bga/Active/gmsroot/:/storage1/fs1/bga/Active/gmsroot/'

# Common vars
GOOGLE_APPLICATION_CREDENTIALS=${HOME}/service-account.json
QUEUE=lims-i2-datatransfer
LOG_FILE=$HOME/gcs_upload.log

bsub -M 512M -R 'select[mem>512M] rusage[mem=512M:internet2_upload_mbps=5000]' \
     -q $QUEUE -G $GROUP -oo $LOG_FILE -N -J $JOB_NAME -u $EMAIL \
     -a 'docker(jackmaruska/cloudize-workflow:0.0.1)' \
     'python3 /opt/cloudize-workflow.py ${GCS_BUCKET} ${WORKFLOW_CWL} ${INPUTS_YAML}'
