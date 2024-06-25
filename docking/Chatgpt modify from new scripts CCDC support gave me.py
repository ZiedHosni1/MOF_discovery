#! /usr/bin/env python

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

CONF_FILE = 'gold.conf'
N_PROCESSES = 6

@dataclass
class Batch:
    n: int
    protein_path: Path
    ligand_path: Path
    conf_file: Path
    output_dir: Path
    dir: Path = field(init=False)

    def __post_init__(self):
        self.dir = self.output_dir / f'chunk_{self.n:02d}'

SCRIPT_INFO = f"""
Script:          {sys.argv[0]}
Platform:        {platform()}
Python exe:      {sys.executable}
Python version:  {'.'.join(str(x) for x in sys.version_info[:3])}
CSD API version: {ccdc.__version__}
"""

def get_logger(name=__name__):
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(asctime)s | %(levelname)s | %(name)s] %(message)s', datefmt='%y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

def do_batch(batch):
    logger = get_logger(f"Batch {batch.n}")

    settings = Docker.Settings().from_file(str(batch.conf_file))

    mkdir(batch.dir)
    chdir(batch.dir)

    settings.output_directory = '.'

    settings.receptor_files = [str(batch.protein_path)]
    settings.clear_ligand_files()
    settings.add_ligand_file(str(batch.ligand_path))

    logger.info(f"Starting docking with protein {batch.protein_path} and ligand {batch.ligand_path}...")

    docker = Docker(settings=settings)
    results = docker.dock()

    logger.info(f"...done")

    return results.return_code

def main():
    logger = get_logger('Main')

    parser = ArgumentParser()
    parser.add_argument('conf_file', nargs='?', default=CONF_FILE, type=str, help=f"GOLD configuration file (default='{CONF_FILE}')")
    parser.add_argument('--protein_dir', required=True, type=str, help="Directory containing protein files")
    parser.add_argument('--ligand_file', required=True, type=str, help="File containing the ligand")
    parser.add_argument('--n_processes', default=N_PROCESSES, type=int, help=f"No. of processes (default={N_PROCESSES})")

    config = parser.parse_args()

    conf_file = Path(config.conf_file)
    protein_dir = Path(config.protein_dir)
    ligand_file = Path(config.ligand_file)
    n_processes = config.n_processes

    if not conf_file.exists():
        logger.error(f"Error! Configuration file '{conf_file}' not found!")
        sys.exit(1)

    if not protein_dir.exists() or not protein_dir.is_dir():
        logger.error(f"Error! Protein directory '{protein_dir}' not found or is not a directory!")
        sys.exit(1)

    if not ligand_file.exists():
        logger.error(f"Error! Ligand file '{ligand_file}' not found!")
        sys.exit(1)

    if not n_processes > 0:
        logger.error(f"Error! Number of processes must be an integer greater than zero.")
        sys.exit(1)

    logger.info(SCRIPT_INFO)

    t0 = time()

    settings = Docker.Settings().from_file(str(conf_file))
    output_dir = Path(settings.output_directory)

    if not str(output_dir) == '.':
        if output_dir.exists():
            logger.error(f"Error! Output dir '{output_dir}' already exists.")
            sys.exit(1)
        mkdir(output_dir)

    protein_files = list(protein_dir.glob('*.pdb'))  # Assuming protein files are in PDB format
    n_proteins = len(protein_files)

    logger.info(f"There are {n_proteins} proteins to dock with the ligand on {n_processes} processes...")

    batches = [Batch(n=i+1, protein_path=protein_files[i], ligand_path=ligand_file, conf_file=conf_file, output_dir=output_dir) for i in range(n_proteins)]

    with Pool(n_processes) as pool:
        _ = pool.map(do_batch, batches)

    logger.info(f"Finished in {time() - t0:.1f} seconds.")

if __name__ == '__main__':
    main()
