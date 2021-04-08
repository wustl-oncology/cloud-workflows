#!/bin/bash
export GCS_BUCKET=griffith-lab-cromwell
export WORKFLOW_CWL=${HOME}/analysis-workflows/definitions/pipelines/rnaseq.cwl
export INPUTS_YAML=${HOME}/human_rna_qc_and_abundance/inputs.yaml
export LSF_DOCKER_VOLUMES='/home/maruska:/home/maruska /storage1/fs1/bga/Active/gmsroot/:/storage1/fs1/bga/Active/gmsroot/'
export GOOGLE_APPLICATION_CREDENTIALS=${HOME}/service-account.json

bsub -M 512M -R 'select[mem>512M] rusage[mem=512M:internet2_upload_mbps=5000]' \
     -q general -G compute-oncology \
     -oo ${HOME}/gcs_upload.log -N \
     -a 'docker(jackmaruska/cloudize-workflow:0.0.1)' \
     -J johnmaruska-gcs-upload -u john.maruska@wustl.edu \
     'python3 /opt/cloudize-workflow.py ${GCS_BUCKET} ${WORKFLOW_CWL} ${INPUTS_YAML}'
