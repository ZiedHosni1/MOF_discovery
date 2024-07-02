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
A user script to generate batch timing statistics.

Call this after job completion.

It extracts the timing information from the Slurm output file.
'''

from pathlib import Path
import re
import statistics

import goldhpc_utilities
logger = goldhpc_utilities.create_logger()


def get_batch_timings_for_jobid(results_dir, job_name, jobid):
    TIMING_REGEX = r'INFO\s+Done in (\d+\.\d+)'
    outfiles = Path(results_dir).glob(f'{job_name}_{jobid}_*.out')
    timings = []
    failed = 0
    for outfile in outfiles:
        with Path(outfile).open() as fh:
            timing = re.findall(TIMING_REGEX, fh.read())
            if len(timing) == 0:
                failed += 1
            else:
                timing = timing[0]
                timings.append(float(timing))
    if failed > 0:
        logger.error(f'{failed} (JobID {jobid}) batches '
                     f'have no timing information')

    logger.info(f'Batch Timing (seconds) for job {jobid}:')
    logger.info(f'  number of tasks: {len(timings)}')
    logger.info(f'  sum: {sum(timings):.3f}')
    if len(timings) < 2:
        logger.error('Insufficient data')
        return sum(timings)
    logger.info(f'  mean: {statistics.mean(timings):.3f}')
    logger.info(f'  median: {statistics.median(timings):.3f}')
    logger.info(f'  standard deviation: {statistics.stdev(timings):.3f}')
    logger.info('  top 3: {}'.format(
        ', '.join([f'{tt:.3f}' for tt in sorted(timings, reverse=True)[:3]])))

    return sum(timings)


def get_batch_timings(results_dir, job_name, slurm_jobid, jobids):
    '''Print timing of batches

    Call after all the tasks have completed.

    :param results_dir: Location of the GOLD docking results to collect
    :type results_dir: str
    :param job_name: The Slurm job name
    :type job_name: str
    :param slurm_jobid: The job ID as returned by sbatch
    :type slurm_jobid: int, optional
    :param jobids: all the job ids found in the jobid.txt
    :type jobids: list of ints, optional
    '''

    total_timing = 0
    if slurm_jobid == 'all':
        for jobid in jobids:
            total_timing += get_batch_timings_for_jobid(results_dir,
                                                        job_name, jobid)
        logger.info(f'Total timing for all the jobs: {total_timing:.3f}')
    else:
        get_batch_timings_for_jobid(results_dir, job_name, slurm_jobid)


def main():
    cs = goldhpc_utilities.ClusterSetting()
    get_batch_timings(cs.output_dir, cs.slurm_settings['JOB_NAME'], cs.jobid,
                      cs.jobids)


if __name__ == '__main__':
    main()
