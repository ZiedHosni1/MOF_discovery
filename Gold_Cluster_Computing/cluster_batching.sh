#!/bin/bash
#! This can be used to perform batching of ligand input on a worker node
#! Run with "sbatch cluster_batching.sh"
#SBATCH -J gold_batching
#SBATCH --output=gold_batching_%A.out
#SBATCH --time=06:00:00

module purge
# If necessary load module for python3

# Get the original location of this script
if [ -n $SLURM_JOB_ID ];  then
    SCRIPT_PATH=$(scontrol show job $SLURM_JOB_ID | awk -F= '/Command=/{print $2}')
else
    SCRIPT_PATH=$(realpath $0)
fi
# The directory that contains all the scripts
GOLDHPC_DIR=$(dirname $SCRIPT_PATH)
python3 ${GOLDHPC_DIR}/cluster_batching.py
