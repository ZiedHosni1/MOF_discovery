#! /usr/bin/env python
########################################################################################################################
#
# This script can be used for any purpose without limitation subject to the
# conditions at http://www.ccdc.cam.ac.uk/Community/Pages/Licences/v2.aspx
#
# This permission notice and the following statement of attribution must be
# included in all copies or substantial portions of this script.
#
# 2020-05-07: created by the Cambridge Crystallographic Data Centre
#
########################################################################################################################

import logging
import sys
from argparse import ArgumentParser
from platform import platform
from pathlib import Path
from os import mkdir, chdir
from shutil import copy
from time import time
from dataclasses import dataclass, field
from multiprocessing import Pool

import ccdc
from ccdc.io import EntryReader
from ccdc.docking import Docker

########################################################################################################################
#
# Program parameters...
#

# Default GOLD conf file to use...

CONF_FILE = 'gold.conf'

# Default number of parallel processes to use...

N_PROCESSES = 6

########################################################################################################################

# Record type to hold the parameters defining a batch...

@dataclass
class Batch:

    n: int                        # Batch number
    start: int                    # Index of first MOF in batch
    finish: int                   # Index of last MOF in batch
    conf_file: Path               # GOLD configuration file
    output_dir: Path              # Output dir, in which the batch sub-directory will be created
    mof_files: list               # List of MOF files to process in this batch
    dir: Path = field(init=False) # Sub-directory for batch, see __post_init__ below

    def __post_init__(self):

        self.dir = self.output_dir / f'chunk_{self.n:02d}'  # Directory will be created in do_chunk function

########################################################################################################################

# A summary of information about the script and where it is running, useful for debugging etc...

SCRIPT_INFO = f"""
Script:          {sys.argv[0]}
Platform:        {platform()}
Python exe:      {sys.executable}
Python version:  {'.'.join(str(x) for x in sys.version_info[:3])}
CSD API version: {ccdc.__version__}
"""

########################################################################################################################

def get_logger(name=__name__):
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(asctime)s | %(levelname)s | %(name)s] %(message)s', datefmt='%y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def do_batch(batch):

    """
    Dock a batch of MOFs.

    :param batch: a record holding the parameters defining the batch

    As we can't return a GOLD results object from a pool process (it can't be pickled as it wraps C++ objects),
    we simply return a boolean recording whether GOLD exited with a 'success' status code.
    """

    logger = get_logger(f"Batch {batch.n}")

    ######

    # As Settings objects cannot be pickled they cannot be passed to pool processes, so we create a fresh copy...

    settings = Docker.Settings().from_file(str(batch.conf_file))

    # Create and enter the sub-directory for this batch...

    mkdir(batch.dir)

    chdir(batch.dir)

    settings.output_directory = '.'  # Ensure GOLD writes output to the batch sub-directory

    # Specify the amino acid ligand file...

    ligand_file = settings.ligand_files[0]

    settings.clear_ligand_files()
    settings.add_ligand_file(ligand_file.file_name)

    # Process each MOF in the batch...

    for index, mof_file in enumerate(batch.mof_files, start=batch.start):

        settings.receptor_files = [mof_file]

        # Run docking...

        logger.info(f"Starting MOF {index} (file {mof_file})...")

        docker = Docker(settings=settings)
        results = docker.dock()

        logger.info(f"...done MOF {index}")

        # Save results...

        for i, result in enumerate(results.poses):
            result.write(f'gold_soln_{index:05d}_{i+1}.mol2')

    return True

########################################################################################################################

def main():

    """
    Dock the MOFs from the supplied input file in parallel.
    """

    logger = get_logger('Main')

    parser = ArgumentParser()

    parser.add_argument('conf_file', nargs='?', default=CONF_FILE, type=str, help=f"GOLD configuration file (default='{CONF_FILE}')")
    parser.add_argument('--n_processes', default=N_PROCESSES, type=int, help=f"No. of processes (default={N_PROCESSES})")
    parser.add_argument('--mof_input_file', type=str, required=True, help="File containing list of MOF files to dock")
    parser.add_argument('--amino_acid_file', type=str, required=True, help="Amino acid file")

    config = parser.parse_args()

    conf_file = Path(config.conf_file)
    n_processes = config.n_processes
    mof_input_file = Path(config.mof_input_file)
    amino_acid_file = Path(config.amino_acid_file)

    if not conf_file.exists():
        logger.error(f"Error! Configuration file '{conf_file}' not found!", file=sys.stderr)
        sys.exit(1)

    if not n_processes > 0:
        logger.error(f"Error! Number of processes must be an integer greater than zero.")
        sys.exit(1)

    if not mof_input_file.exists():
        logger.error(f"Error! MOF input file '{mof_input_file}' not found!", file=sys.stderr)
        sys.exit(1)

    # Read MOF files from the input file
    with mof_input_file.open('r') as f:
        mof_files = [Path(line.strip()) for line in f if line.strip()]

    if len(mof_files) == 0:
        logger.error(f"Error! No MOF files found in '{mof_input_file}'", file=sys.stderr)
        sys.exit(1)

    logger.info(SCRIPT_INFO)

    t0 = time()

    ######

    # Load setting from GOLD conf file...

    settings = Docker.Settings().from_file(str(conf_file))

    # Ensure the output directory exists (a sub-directory for each batch is created within it)...

    output_dir = Path(settings.output_directory)

    if not str(output_dir) == '.':  # Skip directory (re)creation if output dir is current directory

        if output_dir.exists():
            logger.error(f"Error! Output dir '{output_dir}' already exists.")
            sys.exit(1)

        mkdir(output_dir)

    n_mofs = len(mof_files)
    logger.info(f"There are {n_mofs} MOFs to dock on {n_processes} processes...")

    ######

    # Determine the sets of parameters defining the batches...

    basic_size, remainder = n_mofs // n_processes, n_mofs % n_processes

    batches, start = [], 0

    for chunk_n in range(n_processes):

        finish = start + basic_size + (1 if chunk_n < remainder else 0)
        batch_mof_files = mof_files[start:finish]

        batches.append(Batch(n=chunk_n + 1, start=start + 1, finish=finish, conf_file=conf_file, output_dir=output_dir, mof_files=batch_mof_files))

        start = finish

    ######

    # Dock the batches in parallel...

    with Pool(n_processes) as pool:
        pool.map(do_batch, batches)

    ######

    # Combine output from batches into output directory...

    for batch in batches:
        for soln_file in batch.dir.glob('gold_soln_*'):
            copy(str(soln_file), output_dir)

    ######

    # All done.

    logger.info(f"Finished in {time() - t0:.1f} seconds.")

########################################################################################################################

if __name__ == '__main__':
    main()

########################################################################################################################
# End
########################################################################################################################
