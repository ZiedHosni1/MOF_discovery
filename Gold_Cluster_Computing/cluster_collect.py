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
A user script to collect results after job completion.

It creates two directories:
1. hermes - useful for load the results in hermes.
2. bestranking - a merged and sorted bestranking.lst.

'''

import goldhpc_utilities


def main():
    cs = goldhpc_utilities.ClusterSetting()
    cr = goldhpc_utilities.CollectResult(cs.output_dir, cs.jobids, cs.jobid)

    cr.merge_hermes_files('solutions')
    cr.merge_bestranking()


if __name__ == '__main__':
    main()
