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
A user script to resume the submission of GOLD docking jobs.

It first get the last job id from the jobid.txt file, and then go to the
OUTPUT_DIR/{jobid} to read the batches.txt. Compare the batches id and the id
of the results tar file id, and work out the missing results, and write the
corresponding batch ids that have no results returned into resume_batches.txt
which will get copied over into the new result dir as batches.txt, and new
sbatch job gets submitted, the docking maps to the batch ids in the
batches.txt in the result dir.

It creates the following file:
1. resume_batches.txt - to record the batches to be resumed in submission.

'''

import os

import goldhpc_utilities


def write_resume_batches(jobids, output_dir):
    # Work out which batch results are missing, and write to the
    # resume_batches.txt

    resume_batches = []

    for jobid in jobids:
        out_path = f'{output_dir}/{jobid}'
        if not os.path.isfile(f'{out_path}/batches.txt'):
            print(f'{out_path}/batches.txt')
            return f'batches.txt is missing in {out_path}'

        with open(f'{out_path}/batches.txt') as f:
            batches = f.read().splitlines()
            for task_id in range(len(batches)):
                out_file = f'{out_path}/output_{jobid}_{task_id+1}.tar.gz'
                if not os.path.isfile(out_file):
                    resume_batches.append(batches[task_id])

    with open('resume_batches.txt', 'w') as resume_f:
        resume_f.write('\n'.join(resume_batches) + '\n')

    return ''


def main():
    # Read from jobid.txt, get the last job id
    cs = goldhpc_utilities.ClusterSetting(need_jobid=False)

    # Cancel the old jobs in case they still remain in slurm
    for jobid in cs.jobids:
        os.system(f'scancel {jobid}')
        print(f'Job ID {jobid} cancelled')

    error = write_resume_batches(cs.jobids, cs.output_dir)

    if error == '':
        if os.stat("resume_batches.txt").st_size == 0:
            print('All batches have completed docking, no need to resume')
        else:
            os.environ['RESUME_SUBMIT'] = 'true'
            os.system(str(goldhpc_utilities.GOLDHPC_DIR / 'cluster_submit.py'))
            os.environ.pop('RESUME_SUBMIT')
    else:
        print(f'Cluster docking cannot be resumed, due to error {error}')
        print('You may want to run cluster_submit.py to start from beginning')


if __name__ == '__main__':
    main()
