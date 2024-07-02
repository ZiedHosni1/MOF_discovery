#!/bin/bash

module purge
# If required, uncomment the lines below and adjust for your system
# module load singularity
# module load python3

singularity exec --bind ${SHARED_FILESYSTEM},${GOLDHPC_DIR} ${GOLDHPC_DIR}/${GOLDIMAGE} python3 ${GOLDHPC_DIR}/cluster_docking.py "${CCDC_LICENSING_CONFIGURATION}" "${OUTPUT_DIR}" "${GOLD_LOG_LEVEL}"
