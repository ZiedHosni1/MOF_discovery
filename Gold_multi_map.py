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
#
# This script is designed to illustrate how to use the CSD Docking API and the standard multiprocessing module to
# parallelize GOLD docking. It partitions the input ligand file into chunks and uses the multiprocessing 'map' feature
# to dock these chunks in parallel. The default API docking mode is used, which runs GOLD as a subprocess. All output is
# thus written exactly as if GOLD were to be run via Hermes or the command line. The solution files for the chunks are
# copied to the main output directory and the full 'bestranking.lst' file compiled from the partial chunk versions.
#
########################################################################################################################


import sys
from argparse import ArgumentParser
from platform import platform
from pathlib import Path
from os import mkdir, chdir
from shutil import rmtree, copy as cp
from time import time
from dataclasses import dataclass, field
from multiprocessing import Pool

import ccdc
from ccdc.io import csd_version, EntryReader
from ccdc.docking import Docker

########################################################################################################################
#
# Program parameters...
#

# Default GOLD conf file to use...

CONF_FILE = "C:\\Users\juice\PycharmProjects\MOF_discovery_Zyiao_2\gold.conf"

# Default number of parallel processes to use...

N_PROCESSES = 6

# Note that, although the number of chunks is currently the same as the number of processes, it could in theory
# be greater. One  reason to do this might be to ensure that a contiguous  block of large, flexible molecules
# in the input file don't make one chunk run very much slower than the others. There is a cost to starting up
# new instances of GOLD, however, so care should be taken with this.

########################################################################################################################

# Record type to hold the parameters defining a chunk...

@dataclass
class Chunk:

    n: int       # Chunk number
    start: int   # Index of first molecule in chunk
    finish: int  # Index of last molecule in chunk
    conf_file: Path   # GOLD configuration file
    output_dir: Path  # Output dir, in which the chunk sub-directory will be created
    dir: Path = field(init=False) # Sub-directory for chunk, see __post_init__ below

    def __post_init__(self):

        self.dir = self.output_dir / f'chunk_{self.n:02d}'  # Directory will be created in do_chunk function

########################################################################################################################

# A summary of information about the script and where it is running, useful for debugging etc...

SCRIPT_INFO = f"""
Script:         {sys.argv[0]}
Platform:       {platform()}
Python exe:     {sys.executable}
Python version: {'.'.join(str(x) for x in sys.version_info[:3])}
API version:    {ccdc.__version__}
CSD version:    {csd_version()}
"""

########################################################################################################################

def do_chunk(chunk):

    """
    Dock a chunk of the input file.

    :param chunk: a record holding the parameters defining the chunk

    As we can't return a GOLD results object from a pool process (it can't be pickled as it wraps C++ objects),
    we simply return a boolean recording whether GOLD exited with a 'success' status code.
    """

    # As Settings objects cannot be pickled they cannot be passed to pool processes, so we create a fresh copy...

    settings = Docker.Settings().from_file(str(chunk.conf_file))

    # Create and enter the sub-directory for this chunk...

    mkdir(chunk.dir)

    chdir(chunk.dir)

    settings.output_directory = '.'  # Ensure GOLD writes output to the chunk sub-directory

    # Specify the chunk of molecules to dock...

    ligand_file = settings.ligand_files[0]  # The ligand file info will be overwritten, so store for reference below

    settings.clear_ligand_files()

    settings.add_ligand_file(ligand_file.file_name, ndocks=ligand_file.ndocks, start=chunk.start, finish=chunk.finish)

    # Run docking...

    print(f"Starting chunk {chunk.n} (ligand indices {chunk.start} - {chunk.finish})...")

    docker = Docker(settings=settings)

    results = docker.dock()

    print(f"Finished chunk {chunk.n}.")

    # As we can't return the results (as they are not picklable) and the poses have already been written to disk, we just return the status code

    return results.return_code

########################################################################################################################

def main():

    """
    Dock the molecules from the supplied input file in parallel.
    """

    t0 = time()  # Script start time

    parser = ArgumentParser()
    parser.add_argument('conf_file', nargs='?', default=CONF_FILE, type=str, help=f"GOLD configuration file (default='{CONF_FILE}')")
    parser.add_argument('--n_processes', default=N_PROCESSES, type=int, help=f"No. of processes (default={N_PROCESSES})")
    config = parser.parse_args()

    conf_file = Path(config.conf_file)
    n_processes = config.n_processes

    if not conf_file.exists():
        print(f"Error! Configuration file '{conf_file}' not found!", file=sys.stderr)
        sys.exit(1)

    if not n_processes > 0:
        print(f"Error! Number of processes must be an integer greater than zero.")
        sys.exit(1)

    print(SCRIPT_INFO)  # Useful debug info

    ######

    # Load setting from GOLD conf file...

    settings = Docker.Settings().from_file(str(conf_file))

    # Count the molecules to dock in the input file...

    input_file = Path(settings.ligand_files[0].file_name)

    with EntryReader(str(input_file)) as reader:

        n_molecules = len(reader)

    print(f"There are {n_molecules} molecules to dock on {n_processes} processes...")

    # Ensure the output directory exists (a sub-directory for each chunk is created within it)...

    output_dir = Path(settings.output_directory)

    if not str(output_dir) == '.':  # Skip directory (re)creation if output dir is current directory

        if output_dir.exists():

            rmtree(output_dir)

        mkdir(output_dir)

    ######

    # Determine the sets of parameters defining the chunks...

    chunks = []  # List of records that define the chunks

    # Work out the size of each chunk, and hence the start and finish indices in the input file...

    basic_size = n_molecules // n_processes  # Basic size of a chunk, which must obviously be integral
    remainder  = n_molecules %  n_processes  # Number of molecules that would not be included in basic-sized chunks

    finish = 0  # Finish index

    for n in range(1, n_processes + 1):  # Recall that the number of chunks is the same as the number of processes

        start = finish + 1  # Start index

        chunk_size = basic_size + 1 if n <= remainder else basic_size  # Add one to the basic chunk sizes until the remainder are taken care of

        finish = start + chunk_size - 1

        chunks.append(Chunk(n=n, start=start, finish=finish, conf_file=conf_file, output_dir=output_dir))

        print(f"chunk {n}: size: {chunk_size}; start: {start}, finish: {finish}.")

    ######

    # Dock the chunks in parallel...

    with Pool(n_processes) as pool:

        _ = pool.map(do_chunk, chunks)  # We are not currently checking the return codes

    print(f"Finished docking in {time() - t0:.1f} seconds.")

    ######

    # Combine output from chunks into output directory and write combined 'bestranking.lst' file...

    bestranking, preabmle_and_header = [], None  # Records and preamble plus data header from individual chunk 'bestranking.lst' files

    for chunk in chunks:

        # Copy solution files...

        for soln_file in chunk.dir.glob('gold_soln_*'):

            cp(str(soln_file), output_dir)

        # Load records from 'bestranking.lst' file, fixing file paths as we go...

        with (chunk.dir / 'bestranking.lst').open('r') as file:

            lines = [x.replace(str(chunk.dir), str(output_dir)).replace('\\.\\', '\\') for x in file.read().split('\n')]

        if chunk.n == 1:  # Take preamble and data header from first chunk only

            preabmle_and_header = lines[:7]

        bestranking.extend(lines[7:-1])  # Records

    # Write 'bestranking.lst' file...

    with (output_dir / 'bestranking.lst').open('w') as file:

        file.write('\n'.join(preabmle_and_header) + '\n')  # Preamble and data header

        file.write('\n'.join(bestranking) + '\n')  # Records

    # Copy over any other required files from first chunk directory...

    chunk_dir = chunks[0].dir

    for file_name in ['gold_protein.mol2']:

        cp(str(chunk_dir / file_name), output_dir)

    ######

    # All done.

    print(f"Finished in {time() - t0:.1f} seconds.")

########################################################################################################################

if __name__ == '__main__':

    main()

########################################################################################################################
# End
########################################################################################################################