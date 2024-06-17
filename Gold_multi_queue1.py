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
# parallelize GOLD docking. It uses a multiprocessing job queue and a set of worker processes to dock ligands
# from the input file individually. The API 'interactive' docking mode is used, which starts a special GOLD process
# in the background and communicates with it via a socket. GOLD running in this mode doesn't produce the same output
# as it would normally. Thus, output is written explicitly by the script.
#
########################################################################################################################

import sys
from argparse import ArgumentParser
from platform import platform
from pathlib import Path
from os import mkdir, chdir
from shutil import rmtree, copy as cp
from time import time
from operator import itemgetter
from multiprocessing import Process, Queue

import ccdc
from ccdc.io import csd_version, EntryReader, EntryWriter
from ccdc.entry import Entry
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

def worker(input_queue, output_queue, worker_n, conf_file):
    """
    Worker function that performs dockings.

    :param input_queue: Queue of molecules to dock.
    :param output_queue: Queue of docked poses.
    :param worker_n: number of worker process, used for name of worker sub-directory, logging etc.
    :param conf_file: GOLD configuration file

    As we can't return a GOLD results object from a pool process (it can't be pickled as it wraps C++ objects),
    we return string representations of the docked poses.
    """

    # As Settings objects cannot be pickled they cannot be passed to pool processes, so we create a fresh copy...

    settings = Docker.Settings().from_file(str(conf_file))

    # Create and enter the sub-directory for this worker...

    worker_dir = Path(settings.output_directory) / f'worker_{worker_n:02d}'

    mkdir(worker_dir)

    chdir(worker_dir)

    settings.output_directory = '.'  # Ensure GOLD writes output to the worker sub-directory

    # We clear the input file from the settings object as we will be using the queue for input.
    # However, we do need to retain number of docking runs required.

    ndocks = settings.ligand_files[0].ndocks

    settings.clear_ligand_files()

    settings.set_hostname(ndocks=ndocks)

    # Set up an 'interactive' docker, to which molecules will be supplied from the input queue...

    docker = Docker(settings=settings)

    session = docker.dock(mode='interactive')

    session.ligand_preparation = None  # It is assumed that all ligand preparation has already been done

    print(f"Worker {worker_n}: started with GOLD PID {session.pid}.")

    # Dock molecules from the input queue until the stop sentinel is encountered...
    # Note that the index is the molecules' position in the input file, and is used in GOLD output file names (see below).

    for index, entry_string in iter(input_queue.get, 'STOP'):
        entry = Entry.from_string(entry_string)  # Regenerate entry from string representation

        t0 = time()  # Start time

        results = session.dock(entry)

        time_taken = time() - t0  # time taken

        # As we the results objects are not picklable, we must return the string representations of the pose objects...

        poses = [pose.to_string() for pose in results]

        output_queue.put([index, poses, time_taken])

    # Stop sentinel encountered; when this worker function returns the socket to GOLD will be closed and it will shut down.

    print(f"Worker {worker_n}: shutting down.")


########################################################################################################################

def main():
    """
    Dock the molecules from the supplied input file in parallel.
    """

    t0 = time()  # Script start time

    parser = ArgumentParser()
    parser.add_argument('conf_file', nargs='?', default=CONF_FILE, type=str,
                        help=f"GOLD configuration file (default='{CONF_FILE}')")
    parser.add_argument('--n_processes', default=N_PROCESSES, type=int,
                        help=f"No. of processes (default={N_PROCESSES})")
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

    #####

    # Load setting from GOLD conf file...

    settings = Docker.Settings().from_file(str(conf_file))

    # Read the molecules to dock from the input file...
    # Note that we can't pass molecule objects directly to the worker processes as they cannot be pickled, so we use the
    # string representation instead. Note also that we actually use Entry objects so that any attributes are preserved.
    # We store a molecule's index (i.e. it's position in the input file) as it is used in GOLD output file names (see below).

    input_file = Path(settings.ligand_files[0].file_name)

    with EntryReader(str(input_file)) as reader:

        molecules = [[index, entry.to_string()] for index, entry in enumerate(reader, 1)]

    n_molecules = len(molecules)

    print(f"There are {n_molecules} molecules to dock on {n_processes} processes...")

    # Ensure the output directory exists (a sub-directory for each worker process is created within it)...

    output_dir = Path(settings.output_directory)

    if not str(output_dir) == '.':  # Skip directory (re)creation if output dir is current directory

        if output_dir.exists():
            rmtree(output_dir)

        mkdir(output_dir)

    ######

    # Create input and output queues...

    input_queue = Queue()
    output_queue = Queue()

    # Submit the molecules for docking to the input queue...

    for molecule in molecules:
        input_queue.put(molecule)

    # Start the worker processes and run the dockings in parallel...

    for worker_n in range(n_processes):
        Process(target=worker, args=(input_queue, output_queue, worker_n, conf_file)).start()

    # Wait until we have obtained results for all molecules from the output queue...

    results = [output_queue.get() for _ in range(n_molecules)]

    # Use the input queue to shut down the worker processes...

    for _ in range(n_processes):
        input_queue.put('STOP')

    ######

    # Write the docked poses and the 'bestranking.lst' file for each molecule to the output directory, ...

    bestranking, header = [], None  # Best ranking pose for each molecule and data header for the 'bestranking.lst' file

    for index, poses, time_taken in sorted(results, key=itemgetter(0)):  # Results are sorted on molecule index

        best = {'score': sys.float_info.min}  # Best ranking pose for the molecule

        for n_pose, pose in enumerate(poses, 1):

            entry = Entry.from_string(pose)

            file_name = output_dir / f'gold_soln_{input_file.stem}_m{index}_{n_pose}{input_file.suffix}'

            with EntryWriter(str(file_name)) as writer:

                writer.write(entry)

            # For 'bestranking.lst' file...

            header, data = entry.attributes['Gold.Score'].split('\n')  # Note that the header is always the same

            score = float(data.split()[0])

            if score > best['score']:
                best['score'], best['data'], best['file_name'] = score, data, file_name

            if n_pose == 1:  # When on the first pose for a molecule, record it's name and time taken for docking

                best['ligand_name'], best['time'] = entry.identifier.split('|')[0], time_taken

        bestranking.append(best)  # Save record for 'bestranking.lst' file

    # Write 'bestranking.lst' file...

    with (output_dir / 'bestranking.lst').open('w') as file:

        file.write(
            "# File containing a listing of the fitness of the top-ranked\n# individual for each ligand docked in GOLD.\n#\n# Format is:\n#\n")  # Preamble

        file.write(
            f"#     {header}     time                               File name                Ligand name\n\n")  # Data header

        for best in bestranking:  # Records

            file.write(
                f"""     {best['data']}   {best['time']:7.3f}  '{best["file_name"]}'         '{best["ligand_name"]}'\n""")

    # Copy over any other required files from first worker directory...

    worker_dir = output_dir / 'worker_00'

    for file_name in ['gold_protein.mol2']:
        cp(str(worker_dir / file_name), output_dir)

    ######

    # All done.

    print(f"Finished in {time() - t0:.1f} seconds.")


########################################################################################################################

if __name__ == '__main__':
    main()

########################################################################################################################
# End
########################################################################################################################