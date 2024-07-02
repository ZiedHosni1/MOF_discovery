#!/usr/bin/env python3
#
# This script can be used for any purpose without limitation subject to the
# conditions at http://www.ccdc.cam.ac.uk/Community/Pages/Licences/v2.aspx
#
# This permission notice and the following statement of attribution must be
# included in all copies or substantial portions of this script.
#
# 2020-09-15: created by the Cambridge Crystallographic Data Centre
#
'''
A user script to submit GOLD docking jobs.

It calls sbatch to submit the job array. A job array task will read the
batch.txt file and pick the right batch to process based on its slurm task ID.

It creates two files:
1. jobid.txt - to record the Slurm job ID.
2. starttime.txt - to record the start time of job.

'''

from pathlib import Path
import os
import subprocess
import re
import time
import math
import sys

import goldhpc_utilities
from goldhpc_utilities import GOLDHPC_DIR
logger = goldhpc_utilities.create_logger()


class SlurmSetting():
    """A convenience class for HPC cluster slurm settings."""
    def __init__(self, settings, output_dir, job_array):
        """Initiate SlurmSetting"""
        self.settings = settings
        self.output_dir = output_dir
        self.job_array = job_array

    def generate_sbatch_options(self, dependent_jobid=None):
        SLURM_OPTIONS = {
                self.settings['ACCOUNT_NAME']: '--account',
                self.settings['JOB_NAME']: '--job-name',
                self.settings['NODES']: '--nodes',
                self.settings['PARTITION']: '--partition',
                self.settings['TIME_OUT']: '--time',
                }
        slurm_options = f"--output={self.output_dir}/gold_docking_%A_%a.out"
        slurm_options += f" --array=1-{self.job_array}"
        slurm_options += f"%{self.settings['MAX_RUNNING_TASKS']}"
        slurm_options += " --ntasks=1"
        for setting, option in SLURM_OPTIONS.items():
            slurm_options += f" {option}={setting}"
        if dependent_jobid is not None:
            slurm_options += f" --dependency=afterany:{dependent_jobid}"
        slurm_options += f" {self.settings.get('OTHER_SBATCH_OPTIONS', '')}"
        return slurm_options


def array_end_indices(n_batch, step_size):
    indices = [step_size for i in range(math.floor(n_batch / step_size))]
    if n_batch % step_size != 0:
        indices.append(n_batch % step_size)
    return indices


def main():
    cs = goldhpc_utilities.ClusterSetting(need_jobid=False)

    os.environ['GOLD_LOG_LEVEL'] = cs.gold_settings['GOLD_LOG_LEVEL']
    os.environ['CCDC_LICENSING_CONFIGURATION'] = \
        cs.gold_settings['CCDC_LICENSING_CONFIGURATION']
    os.environ['GOLDIMAGE'] = cs.gold_settings['GOLDIMAGE']
    os.environ['SHARED_FILESYSTEM'] = cs.shared_dir
    os.environ['INPUT_DIR'] = cs.input_dir
    os.environ['OUTPUT_DIR'] = cs.output_dir
    os.environ['GOLDHPC_DIR'] = str(GOLDHPC_DIR)
    Path(cs.output_dir).mkdir(parents=True, exist_ok=True)

    # Perform batch file checks and read the list of batch files.
    batchfile_name = 'resume_batches.txt' if 'RESUME_SUBMIT' in os.environ \
        else 'batches.txt'
    batchfile_path = Path(batchfile_name)
    if not batchfile_path.exists():
        logger.error(f"File {batchfile_name} can't be found, "
                     "please check the file was created during batching.")
        sys.exit(1)
    with batchfile_path.open() as open_batchfile:
        batch_files = open_batchfile.readlines()
    first_batch = Path(batch_files[0].strip())
    if not first_batch.exists():
        logger.error(f"Batch file {str(first_batch)} does not exist.")
        logger.error(f"Please check and update the batch file paths in file "
                     f"{batchfile_name}")
        sys.exit(1)

    # Depending on the number of batches and the value of Slurm param
    # MaxArraySize decide the number of sbatch calls we need to make.
    max_array_size = int(cs.slurm_settings['MAX_ARRAY_SIZE'])
    logger.info(f"MAX_ARRAY_SIZE = {max_array_size}")
    array_indices = array_end_indices(cs.num_array_tasks, max_array_size)

    jobid = None
    batch_file_start = 0
    batch_file_end = 0
    for index in array_indices:
        slurm_setting = SlurmSetting(cs.slurm_settings, cs.output_dir, index)
        slurm_options = slurm_setting.generate_sbatch_options(
            dependent_jobid=jobid)
        sbatch_command = (f"sbatch {slurm_options} " +
                          f"{str(GOLDHPC_DIR / 'cluster.sh')}")
        print(sbatch_command)
        completed_process = subprocess.run(sbatch_command.split(),
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT)
        sbatch_output = completed_process.stdout.decode()
        print(sbatch_output)
        jobid_regex = r'^Submitted batch job (\d+)$'
        jobid = re.match(jobid_regex, sbatch_output).group(1)

        job_out_dir = f'{cs.output_dir}/{jobid}'
        Path(job_out_dir).mkdir(parents=True, exist_ok=True)

        with open(f'{job_out_dir}/batches.txt', 'w') as job_batch_file:
            batch_file_start = batch_file_end
            batch_file_end += index
            job_batch_file.writelines(
                batch_files[batch_file_start:batch_file_end])

        with open('jobid.txt', 'a+') as f:
            f.write(f'{jobid}\n')

    Path('starttime.txt').write_text(str(time.time()))


if __name__ == '__main__':
    main()
