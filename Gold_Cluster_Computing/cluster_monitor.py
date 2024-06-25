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
A user script to monitor job progress.

It calls squeue to determine the status of the tasks.
'''

from collections import defaultdict
from pathlib import Path
import re
import shlex
import subprocess
import time

import goldhpc_utilities
logger = goldhpc_utilities.create_logger()


def send_system_command(command_str):
    """Send a command to the system and return the output"""
    p = subprocess.Popen(shlex.split(command_str), stdout=subprocess.PIPE)
    cmd_output, _ = p.communicate()
    return cmd_output.decode()


class HPCMonitor():
    """Return useful status of current jobs"""
    def __init__(self, jobname, slurm_jobids, output_dir, interval=60):
        """Initiate HPC monitor.

        :param jobname: Job name
        :type jobname: str
        :param slurm_jobid: The job ID as returned by sbatch
        :type slurm_jobid: int
        :param arrayjobs: The total number of array jobs
        :type arrayjobs: int
        :param interval: The interval (seconds) between each poll,
            defaults to 60
        :type interval: int
        """
        self.jobname = jobname
        self.slurm_jobids = slurm_jobids
        self.output_dir = output_dir
        self.interval = interval

    def get_queue(self, jobid):
        """Return a tuple of number of tasks in queue and running"""
        cmd = (f'squeue -h -n {self.jobname} -j {jobid} -o "%i %t %r"')
        output = send_system_command(cmd)
        logger.debug(output)

        # Parse output
        counts = defaultdict(int)
        range_regex = rf'^{jobid}_\[(\d+)-(\d+)(%\d+)?\]$'
        single_regex = rf'^{jobid}_\[?(\d+)\]?$'
        for queue_line in output.splitlines():
            jobs, status, reason = queue_line.split(' ', 2)

            # Flag error
            if status in ['BF', 'DL', 'F', 'NF', 'TO']:
                logger.error(f'Job {jobs} failed with status {status} '
                             f'and reason {reason}')
            # Pending for the wrong reason
            if status == 'PD' and reason not in ['JobArrayTaskLimit',
                                                 'None', 'Priority',
                                                 'Resources']:
                logger.warning(f'Job {jobs} is pending because {reason}')
                if reason == 'launch failed requeued held':
                    logger.warning('Try releasing the held job with '
                                   '"scontrol release" or contact support')
            # Keep an eye on CG when there's a valid reason
            if status == 'CG' and reason is not None:
                logger.info(f'Job {jobs} is completing with {reason}')

            m = re.match(single_regex, jobs)
            if m:
                counts[status] += 1
                continue
            m = re.match(range_regex, jobs)
            if m:
                counts[status] += int(m.group(2)) - int(m.group(1)) + 1
                continue
            logger.warning(queue_line)

        return counts['PD'] + counts['CF'], counts['R']

    def _arrayjobs(self, jobid):
        arrayjobs = 0
        batch_txt = Path(self.output_dir) / jobid / "batches.txt"
        if batch_txt.exists():
            with batch_txt.open() as f:
                arrayjobs = len(f.readlines())
        else:
            logger.warning(f"Can't find batches file {str(batch_txt)}")
        return arrayjobs

    def run(self):
        """Run in loop, print progess, until all tasks are finished"""
        try:
            start = float(Path('starttime.txt').read_text())
        except FileNotFoundError:
            start = 0
        for jobid in self.slurm_jobids:
            arrayjobs = self._arrayjobs(jobid)
            if not arrayjobs:
                # If batches.txt is not found, skip monitoring this jobid
                continue
            logger.info(f'Monitoring batch job {jobid} ({arrayjobs} tasks)')
            while True:
                queued, running = self.get_queue(jobid)
                completed = arrayjobs - queued - running
                logger.info(
                    'Completed: {}, Running: {}, Queued: {}, Progress: {}%'
                    .format(completed,
                            running,
                            queued,
                            int(100.0 * completed / arrayjobs)))
                if arrayjobs == completed:
                    logger.info('All done!')
                    if start != 0:
                        logger.info('Time taken: ' +
                                    f'{time.time() - start:.0f} seconds')
                    break
                time.sleep(self.interval)


def main():
    cs = goldhpc_utilities.ClusterSetting()
    mon = HPCMonitor(cs.slurm_settings['JOB_NAME'],
                     cs.jobids,
                     cs.output_dir,
                     interval=30)
    mon.run()


if __name__ == '__main__':
    main()
