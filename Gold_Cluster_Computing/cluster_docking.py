#!/usr/bin/env python
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
A worker script to run off the GOLD worker image.

Takes an argument for the input file (tar).

'''

import logging
import os
import sys
from pathlib import Path

sys.path.append('/ccdc/goldWorker')
import goldhpc  # noqa: E402

job_id = os.environ.get('SLURM_ARRAY_JOB_ID')
task_id = os.environ.get('SLURM_ARRAY_TASK_ID')
ntasks = os.environ.get('SLURM_ARRAY_TASK_COUNT')

# Not ran as slurm array job, exit here.
if task_id is None:
    sys.exit()

logging.info(f'This is task {task_id} of {ntasks}')

# Pick up the batch
out_path = Path(sys.argv[2])
out_file = out_path / job_id / f'output_{job_id}_{task_id}'
batch_file = out_path / job_id / 'batches.txt'
with open(batch_file) as fh:
    batches = fh.read().splitlines()
input_file = batches[int(task_id) - 1]

# Now submit
logging.info(f'Submitting {input_file} for GOLD docking')
goldhpc.GOLD_LOG_LEVEL = int(sys.argv[3])
os.environ['CCDC_LICENSING_CONFIGURATION'] = sys.argv[1]
with open(input_file, 'rb') as gold_input:
    try:
        goldhpc.process_tar(gold_input, output_filename=str(out_file))
    except Exception as exc:
        logging.error(str(exc))
