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
A user script to batch ligands for GOLD docking.

It creates batches.txt - lists the batch tar files for the tasks.

'''

import os
import goldhpc_utilities
logger = goldhpc_utilities.create_logger()


def main():
    cs = goldhpc_utilities.ClusterSetting(need_jobid=False)
    # Generate the batches
    batcher = goldhpc_utilities.LigandBatchGenerator(
             cs.gold_settings['LIGAND_PATH'],
             batch_size=int(cs.gold_settings['BATCH_SIZE']),
             gold_path=cs.gold_settings['GOLD_PATH'],
             output_dir=cs.input_dir,
             write_resume_log=cs.write_resume_log,
             write_batch_mapping=cs.write_batch_mapping)
    batches = list(batcher.batches())
    # Write the batches to file (to be picked up by the array job tasks)
    with open('batches.txt', 'w') as fh:
        fh.write('\n'.join(batches) + '\n')
    logger.info(f'{len(batches)} batches created.')

    # Remove the jobid.txt file after the new batches generation,
    # as it records each job run for this set of batches.
    if os.path.exists('jobid.txt'):
        os.remove('jobid.txt')
        logger.info('jobid.txt removed.')


if __name__ == '__main__':
    main()
