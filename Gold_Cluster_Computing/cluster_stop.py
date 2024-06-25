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
A user script to stop/cancel all the submitted GOLD docking jobs.

It get all the job ids from jobid.txt, and then call the slurm command
scancel to terminate them.

'''

import os

import goldhpc_utilities


def main():
    # Read from jobid.txt, get all the job ids
    cs = goldhpc_utilities.ClusterSetting(need_jobid=False)
    for jobid in cs.jobids:
        os.system(f'scancel {jobid}')
        print(f'Job ID {jobid} cancelled')


if __name__ == '__main__':
    main()
