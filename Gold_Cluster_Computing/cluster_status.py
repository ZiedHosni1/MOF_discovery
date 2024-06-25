#!/usr/bin/env python3
#
# This script can be used for any purpose without limitation subject to the
# conditions at http://www.ccdc.cam.ac.uk/Community/Pages/Licences/v2.aspx
#
# This permission notice and the following statement of attribution must be
# included in all copies or substantial portions of this script.
#
# 2020-09-25: created by the Cambridge Crystallographic Data Centre
#
"""
A user script to check on the status of a GOLD HPC cluster run.

It checks the status of the results.
"""

import re
from pathlib import Path
import tarfile
import goldhpc_utilities


class HPCJobStatus():
    """Report on job completion state and any errors encountered."""

    def __init__(self, job_id, jobids, output_dir, job_name):
        """
        Initialise the Job Status report.

        Args:
            job_id (int): The Slurm batch job ID or 'all'
            output_dir (str): The path to the job output
        """

        self.job_id = job_id
        self.jobids = jobids
        self.output_dir = output_dir
        self.job_name = job_name

    def _completed_for_jobid(self, job_id):
        results_files = []
        out_path = Path(self.output_dir) / str(job_id)
        tar_file_re = re.compile(rf"output_{job_id}_[0-9]+[.]tar[.]gz")
        for f in Path(out_path).iterdir():
            if tar_file_re.search(str(f)):
                results_files.append(f)
        print(f"Job ID {job_id}: {len(results_files)} batches completed "
              f"(results written to {str(out_path)})")

        return len(results_files)

    def _completed(self):
        """Count the number of results output tar.gz files."""
        results_total = 0
        if self.job_id == 'all':
            for jobid in self.jobids:
                results_total += self._completed_for_jobid(jobid)
            print(f'Total {results_total} batches completed for'
                  f' all jobs submitted for the current batches')
        else:
            self._completed_for_jobid(self.job_id)

    def _errors_for_jobid(self, job_id):
        exit_status_str = "GOLD returned non-zero exit status"
        out_path = Path(self.output_dir) / str(job_id)
        out_file_re = \
            re.compile(rf"{self.job_name}_{job_id}_[0-9]+[.]out")
        id_batch_re = re.compile(rf"{job_id}_[0-9]+[.]")
        for f in Path(out_path).iterdir():
            if out_file_re.search(str(f)):
                if exit_status_str in f.read_text():
                    print(f"Error reported in {f.name},"
                          "reading goldworker.err")
                    match = id_batch_re.search(f.name)
                    results_tar = f"output_{match.group(0)}tar.gz"
                    results_tar_p = Path(out_path) / results_tar
                    self._read_goldworker_err(results_tar_p)

    def _errors(self):
        """Check for errors in the job output files."""
        if self.job_id == 'all':
            for jobid in self.jobids:
                self._errors_for_jobid(jobid)
        else:
            self._errors_for_jobid(self.job_id)

    def _read_goldworker_err(self, results_tar):
        if results_tar.exists():
            tar = tarfile.open(results_tar)
            err_found = False
            for member in tar.getmembers():
                if member.name == "goldworker.err":
                    err_found = True
                    f = tar.extractfile(member)
                    lines = f.readlines()
                    for line in lines:
                        print(line.decode())
                    break
            if not err_found:
                print(f"Could not find goldworker.err in {results_tar.name}")
        else:
            print(f"File {results_tar.name} does not exist.")

    def report(self):
        self._completed()
        self._errors()


def main():
    cs = goldhpc_utilities.ClusterSetting()
    hpc_job_status = HPCJobStatus(cs.jobid, cs.jobids, cs.output_dir,
                                  cs.slurm_settings['JOB_NAME'])
    hpc_job_status.report()


if __name__ == '__main__':
    main()
