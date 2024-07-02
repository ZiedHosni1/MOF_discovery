#!/usr/bin/env python
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
A module for GOLD HPC utilities

'''

import argparse
import configparser
import csv
import gzip
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import logging
import sys

GOLDHPC_DIR = Path(__file__).parent.resolve()
CLUSTER_INI = Path.cwd() / 'cluster.ini'

BESTRANKING_FILENAME = 'bestranking.lst'
STRUCTURE_DELIMITERS = {
    'sdf_file': '$$$$',
    'mol2_file': '@<TRIPOS>MOLECULE'
}


def create_logger():
    debug_info_handler = logging.StreamHandler(stream=sys.stdout)
    debug_info_handler.setLevel(logging.DEBUG)
    error_warning_handler = logging.StreamHandler(stream=sys.stderr)
    error_warning_handler.setLevel(logging.WARNING)
    logging.basicConfig(
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=logging.INFO,
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                debug_info_handler,
                error_warning_handler
                ]
            )
    return logging.getLogger(__file__)


create_logger()


class ClusterSetting():
    """A convenience class for the HPC cluster scripts.

    Make a few common properties easily accessible to all the cluster scripts.
    """
    def __init__(self, description='', need_jobid=True):
        """Initiate ClusterSetting

        :param need_jobid: Set to False to indicate that job ID is not expected
            to be specified. For example, pre-submission scripts and scripts
            that are meant to process all job IDs do not expect job ID to be
            specified.
        :type need_jobid: bool, optional
        """
        self.need_jobid = need_jobid
        # Read from jobid.txt the current slurm job ID.
        self.jobid_list = []
        try:
            with open('jobid.txt', 'r') as f:
                self.jobid_list = f.read().splitlines()
        except FileNotFoundError:
            self.jobid_list.append(os.environ.get('SLURM_ARRAY_JOB_ID', 0))
        # Parse optional arguments
        parser = argparse.ArgumentParser(
                description=description,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("-i", "--ini_file",
                            help="The path to the cluster ini config file.",
                            default=CLUSTER_INI
                            )
        if need_jobid:
            parser.add_argument("-j", "--jobid", type=str,
                                help="The Slurm Job ID. The default value, "
                                     "where it is expected, "
                                     "will be dynamically set to the last "
                                     "value in jobid.txt.",
                                default='all'
                                )
        self.args, _ = parser.parse_known_args()

        if need_jobid and self.args.jobid == 0:
            sys.exit('Please specify a valid job ID')

        self.config = configparser.ConfigParser(defaults=os.environ)
        self.config.read(self.args.ini_file)

        # Validate the config
        if 'CCDC_LICENSING_CONFIGURATION' not in self.config['GOLD']:
            raise RuntimeError('GOLD/CCDC_LICENSING_CONFIGURATION not found in cluster.ini')
        license_string = self.config['GOLD']['CCDC_LICENSING_CONFIGURATION']
        _, url, *_ = license_string.split(';')
        if not url.startswith('http://'):
            raise RuntimeError('Error: License server url missing "http://"')

    @property
    def jobid(self):
        return self.args.jobid

    @property
    def jobids(self):
        return self.jobid_list

    @property
    def num_array_tasks(self):
        try:
            if self.need_jobid:
                # After job submission:
                # The batches.txt file is found in the jobid output dir
                job_out_dir = f'{self.output_dir}/{self.jobid}'
                batch_file = Path(job_out_dir) / 'batches.txt'
            else:
                # Before submission:
                # Use the environment variable to determine which file to use
                if 'RESUME_SUBMIT' in os.environ:
                    batch_file = Path('resume_batches.txt')
                else:
                    batch_file = Path('batches.txt')
            num_array_tasks = len(batch_file.read_text().splitlines())
        except FileNotFoundError:
            logging.error(f'{batch_file} not found')
        logging.info(f'Found {num_array_tasks} batches in {batch_file}')
        return num_array_tasks

    @property
    def input_dir(self):
        return self.config['Paths']['INPUT_DIR']

    @property
    def output_dir(self):
        return self.config['Paths']['OUTPUT_DIR']

    @property
    def shared_dir(self):
        return self.config['Paths']['SHARED_FILESYSTEM']

    @property
    def gold_settings(self):
        return self.config['GOLD']

    @property
    def slurm_settings(self):
        return self.config['Slurm']

    @property
    def write_resume_log(self):
        return self.config.getboolean('GOLD', 'WRITE_BATCH_RESUME_LOG',
                                      fallback=False)

    @property
    def write_batch_mapping(self):
        return self.config.getboolean('GOLD', 'WRITE_BATCH_MAPPING',
                                      fallback=False)


class ResumeLog():
    """Supports resume processing of the batch so that a log of the work is
    recorded and can be restarted
    """

    _list_of_resume_items = {}

    RESUME_LOG_FILE = "resumelog.csv"
    FILE_NAME_PROPERTY = "file"
    ORIGINAL_FILE_PROPERTY = "original_file"
    FILE_DELIMITER = "!"
    CSV_DELIMITER = ","
    FIELD_NAMES = [FILE_NAME_PROPERTY, ORIGINAL_FILE_PROPERTY]

    def __init__(self, resume_log_path: str, output_dir=None):
        """Setup the resume log processing

        :arg resume_log_path: {:obj:`str`) The file name used to perform a
            resume
        :param output_dir: The output directory the resume log is written to,
            defaults to None
        :type output_dir: str, optional
        """

        # The absolute path of the resume log (resume the batching from the
        # last processed ligand).
        self.resume_log = Path(resume_log_path) if resume_log_path else None

        # The file handler used to support writing to the resume log
        self.resume_file_handler = None

        # Should we perform a resume
        self.should_resume = False

        # the CSV writer object instance
        self.resume_writer = None

        # check if we have provided a resume log
        if resume_log_path is None:
            self.should_resume = False
            if output_dir is not None:
                self.resume_log = Path(output_dir) / self.RESUME_LOG_FILE
            else:
                self.resume_log = (Path(tempfile.mkdtemp()) /
                                   self.RESUME_LOG_FILE)
            self.create_resume_log()
            self.clear()
            logging.info(f"writing to resume log: {self.resume_log}")
        else:
            self.should_resume = True
            self.resume_log = Path(resume_log_path)
            logging.info(f"reading from the resume log: {self.resume_log}")

    def create_resume_log(self):
        """creates the new resume_log file - removing the existing one if found
        """
        if self.resume_log.is_file():
            self.resume_log.unlink()
        self.resume_file_handler = self.resume_log.open(mode='w', newline='')
        self.create_writer()

    def create_writer(self):
        """creates the resume writer instance for dictionary writes
        called after the read and when writing to the resume log
        """
        self.resume_writer = csv.DictWriter(
            self.resume_file_handler,
            fieldnames=self.FIELD_NAMES,
            delimiter=self.CSV_DELIMITER,
            quoting=csv.QUOTE_MINIMAL)

    def read_resume_log_and_build_list(self):
        """Read the contents of the log file and build up an array of ligands
        we have already processed

        :returns: (:obj:`list`) The list of processed ligands from the resume
            log
        """
        try:
            if self.resume_log.is_file():
                self.resume_file_handler = self.resume_log.open(
                        mode='r+', newline='')
                resume_writer = csv.DictReader(
                    self.resume_file_handler,
                    fieldnames=self.FIELD_NAMES,
                    delimiter=self.CSV_DELIMITER,
                    quoting=csv.QUOTE_MINIMAL,
                    restval='')
                for row in resume_writer:
                    self._list_of_resume_items[row[self.FILE_NAME_PROPERTY]] \
                            = row[self.ORIGINAL_FILE_PROPERTY]
            else:
                self.create_resume_log()
        except IOError:
            logging.info(f"{self.resume_log} Unable to read data from the "
                         "resume log")
        finally:
            # Create the writer so that we can continue from where we left off
            self.create_writer()

    def clear(self):
        """clear any items from the resume list"""
        self._list_of_resume_items.clear()

    def close(self):
        """flushes and closes the resumelog"""
        if self.resume_file_handler:
            logging.info("flush and close resume log")
            self.resume_file_handler.flush()
            self.resume_file_handler.close()
            self.resume_file_handler = None

    def exists(self, filename, original_filename):
        """does the file exist in the dictionary - also checks if the values
        are the same as well

        :arg filename (:obj:`str`) the name of the file (used for the key)
        :arg original_file (:obj:`str`) the name of the original file
            (used for the value)
        """
        return filename in self._list_of_resume_items \
            and self._list_of_resume_items[filename] == original_filename

    def add(self, filename, original_file):
        """adds a new item to the resume list

        :arg filename (:obj:`str`) the name of the file (used for the key)
        :arg original_file (:obj:`str`) the name of the original file
            (used for the value)
        """
        self._list_of_resume_items[filename] = original_file

    def filename(self, file, counter):
        """build up the filename that will be used to index as well as
        identify the original file and structure

        :arg file (:obj:`str`) the name of the file
        :arg counter (:obj:`int`) the structural counter of a ligand in the
            file
        """
        return self.FILE_DELIMITER.join([file, str(counter)])

    def add_ligand_to_resume_log(self, ligand_file, original_file):
        """Write the ligand and structure count to the resume log file

        :arg ligand_file (:obj:`str`) the absolute path to the resume log
        :arg original_file (:obj:`str`) the original file that supports the
            ligands
        """
        if self.resume_writer is not None:
            if not self.exists(ligand_file, original_file):
                self.resume_writer.writerow(
                        {self.FILE_NAME_PROPERTY: ligand_file,
                            self.ORIGINAL_FILE_PROPERTY: original_file})
                self.resume_file_handler.flush()
                self.add(ligand_file, original_file)


class BatchMapping(object):
    """Collect the ligand file names used in each batch.

    Each batch can contain ligands from one or more input files. This class
    is used to store the ligand files that correspond to a single batch. That
    list is then written to the batch mapping file.
    """
    def __init__(self):
        self.files = {}

    def add(self, ligand_file, nligands):
        """Add a ligand file used in this batch.

        :param ligand_file: Original full path to ligand input file.
        :type ligand_file: string
        :param nligands: Number of ligands currently in the batch.
        :type nligands: int
        """
        self.files[ligand_file] = nligands

    def write(self, batch_mapfile, batch_file):
        """Write a batch entry to the Batch Mapping file.

        :param batch_mapfile: Full path to the mapping file
        :type batch_mapfile: string
        :param batch_file: full path to the batch file
        :type batch_file: string
        """
        if self.files:
            with open(batch_mapfile, 'a') as fh:
                fh.write('{}\n\t{}\n'.format(
                            batch_file,
                            '\n\t'.join(self.files.keys())))
            self.files.clear()


class LigandBatchGenerator(object):
    """Generate batches of files for processing by GOLD out of larger sets.

    This will create two temporary directories:
    1. A "tempdir" for individual ligand files and the data tar file.
    2. An "out_dir" for the files to be included in the data tar file.

    There are two ways to specify the data:
    1. Set gold_path (a directory). gold.conf must exist in the directory.
       It should also contain all the data files needed.
    2. Set protein_path (a file) and cavity_path (a file). In this case
       gold.conf must exist in the same directory as the calling script.
    In both cases ligand_path is mandatory. This can be either a file or a
    directory. If it is a directory, any files in subdirectories will also be
    processed.

    If desired, output_dir can be specified to indicate the directory
    the batches should be written to. By default temporary directories
    in $TMP will be created.

    """
    def __init__(self,
                 ligand_path,
                 batch_size=2000,
                 total_batches=0,
                 gold_path=None,
                 protein_path=None,
                 cavity_path=None,
                 output_dir=None,
                 write_resume_log=True,
                 resume_log=None,
                 write_batch_mapping=True
                 ):
        """Set up batch generation and create output directories.

        :param ligand_path: A directory or archive of ligand files to dock.
        :type ligand_path: str
        :param batch_size: The maximum number of ligands to include in a batch,
            defaults to 2000
        :type batch_size: int, optional
        :param total_batches: The total number of batches,
            defaults to 0 (unlimited)
        :type batch_size: int, optional
        :param gold_path: A directory of data required for the docking,
            defaults to None
        :type gold_path: str, optional
        :param protein_path: A protein file to dock the ligands into,
            defaults to None
        :type protein_path: str, optional
        :param cavity_path: A cavity file defining the cavity to use,
            defaults to None
        :type cavity_path: str, optional
        :param output_dir: The output directory the batches are written to,
            defaults to None
        :type output_dir: str, optional
        :param write_resume_log: Whether to write the resume log or not,
            defaults to True
        :type write_resume_log: boolean, optional
        :param resume_log: The absolute path to the resume log file,
            defaults to None
        :type resume_log: str, optional
        :param write_batch_mapping: Whether to write the ligand file to
            batch mapping file, defaults to True
        :type write_batch_mapping: boolean, optional
        """
        # A temporary directory used to extract ligand files into
        self.tempdir = tempfile.mkdtemp()
        # The output directory used to assemble batches in.
        self.out_dir = tempfile.mkdtemp()

        # The absolute path of the data directory to be used.
        self.gold_path = gold_path
        # The absolute path of ligand files to dock.
        self.ligand_path = ligand_path
        # The absolute path of the protein file to dock the ligands on.
        self.protein_path = protein_path
        # The absolute path of the cavity file to dock the ligands on.
        self.cavity_path = cavity_path

        self.batch_size = batch_size
        # If specified, the total number of batches to generate
        self.total_batches = total_batches
        # If specified, the directory the generated batches are written to
        self.output_dir = output_dir
        # The file showing mapping between batches and original ligand files
        if self.output_dir is not None:
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
            self.batch_mapfile = os.path.join(self.output_dir,
                                              'batch_mapping.txt')
        else:
            self.batch_mapfile = os.path.join(self.out_dir,
                                              'batch_mapping.txt')

        # The number of batches generated
        self.batches_done = 0

        # The instance of a resume log
        self.write_resume_log = write_resume_log
        self.resume = ResumeLog(resume_log, output_dir=output_dir) if \
            self.write_resume_log else None

        self.write_batch_mapping = write_batch_mapping

        # Check 1: ligand_path must exist
        if self.ligand_path is None or \
                (not os.path.isfile(self.ligand_path) and
                 not os.path.isdir(self.ligand_path)):
            raise FileNotFoundError(
                    f"{self.ligand_path} not found. "
                    "You must specify a ligand file or a directory of ligands")

        # Check 2: The ligand path directory should not match the gold_path
        # directory (or else whole ligand files will get added to each batch)
        if self.gold_path:
            if os.path.isfile(self.ligand_path):
                ligand_dir = os.path.realpath(
                        os.path.dirname(self.ligand_path))
            else:
                ligand_dir = os.path.realpath(self.ligand_path)
            if ligand_dir == os.path.realpath(self.gold_path):
                raise ValueError(
                        f"The ligand file or directory path {self.ligand_path}"
                        f" must not match the gold_path {self.gold_path}.")

        files_to_include = []
        if self.gold_path:
            self.gold_conf = Path(self.gold_path) / 'gold.conf'
            # Add all the data files in gold_path
            for item in os.listdir(self.gold_path):
                if item == 'gold.conf':
                    continue
                item_path = os.path.join(self.gold_path, item)
                files_to_include.append(item_path)
                if os.path.isfile(item_path):
                    shutil.copy(os.path.abspath(item_path), self.out_dir)
                elif os.path.isdir(item_path):
                    shutil.copytree(os.path.abspath(item_path),
                                    os.path.join(self.out_dir, item))
            if len(files_to_include) == 0:
                raise ValueError(f"Cannot find any additional files in the "
                                 f"gold_path {self.gold_path}")
        else:
            self.gold_conf = Path(__file__).parent.resolve() / 'gold.conf'
            if self.protein_path is None or \
                    not os.path.isfile(self.protein_path):
                raise FileNotFoundError(
                        f'Could not find protein file {self.protein_path}. '
                        'Please check the supplied path.')
            files_to_include.append(self.protein_path)
            if self.cavity_path is None or \
                    not os.path.isfile(self.cavity_path):
                raise FileNotFoundError(
                        f'Could not find cavity file {self.cavity_path}. '
                        'Please check the supplied path.')
            files_to_include.append(self.cavity_path)
            for file_name in files_to_include:
                shutil.copy(file_name, self.out_dir)

        # check the conf file has the required replacement fields
        # and run other additional pre-flight checks
        with self.gold_conf.open() as conf_file:
            contents = conf_file.read()
            if self.gold_path and "{ligand_data_file}" not in contents:
                raise ValueError("The '{ligand_data_file}' replacement field "
                                 "is missing from the gold.conf file")
            elif not self.gold_path and not all(
                    [(rf in contents) for rf in ["{ligand_data_file}",
                                                 "{cavity_data_file}",
                                                 "{protein_data_file}"]]):
                raise ValueError("The gold.conf file is missing one or more "
                                 "of the required file replacement fields")

            # The output directory must be set to 'output'.
            if "directory = output" not in contents:
                raise ValueError("The gold.conf output directory must be set "
                                 "to 'directory = output'")

    def tarball_batch(self, ligand_data_file, protein_data_file,
                      cavity_data_file, source_ligandfiles=None):
        """Pack up everything in the output directory for use as a work item.

        The arguments passed in are used to edit the template gold.conf file
        to use the correct paths for the relevant files.

        Pass in an optional source_ligandfiles to create a mapping of the
        generated batch file and the original ligand file.

        :param ligand_data_file: The name of the ligand data file.
        :type ligand_data_file: str
        :param protein_data_file: The name of the protein data file.
        :type protein_data_file: str
        :param cavity_data_file: The name of the cavity data file.
        :type cavity_data_file: str
        :param source_ligandfiles: The set of the original ligand file,
            defaults to None
        :type source_ligandfiles: BatchMapping(), optional

        :returns: The full path of the tar archive containing the docking set.
        """
        # A new .tar.gz file for storing batches
        batch_filename = f'batch_{self.batches_done:08}.tar.gz'
        if self.output_dir is not None:
            file_name = os.path.join(self.output_dir, batch_filename)
        else:
            file_name = os.path.join(tempfile.mkdtemp(), batch_filename)
        if source_ligandfiles is not None:
            source_ligandfiles.write(self.batch_mapfile, file_name)

        # Read the gold.conf file and re-write it, replacing
        # {{ligand_data_file}} with the correct file name for the extension
        # on the source data.
        with self.gold_conf.open() as template, \
                open(os.path.join(self.out_dir, 'gold.conf'), 'w') as out_conf:

            if protein_data_file is None:
                conf_file_text = template.read().format(
                        ligand_data_file=ligand_data_file)
            else:
                conf_file_text = template.read().format(
                        ligand_data_file=ligand_data_file,
                        protein_data_file=os.path.basename(protein_data_file),
                        cavity_data_file=os.path.basename(cavity_data_file))

            out_conf.write(conf_file_text)

        with tarfile.open(file_name, mode='w:gz', compresslevel=1) as tar:
            # arcname='' will strip out any relative path names for the files
            # being added
            tar.add(self.out_dir, arcname='')

        return file_name

    @staticmethod
    def extract_mol2_structure_lines(file_handle):
        """Extract a single structure from a mol2 file handle.

        Mol2 extraction is complicated by the lack of a terminator string so
        once we hit the next molecule move the file object's position back
        to the previous line.

        :param file_handle: an open ligand mol2 file handle
        :type file_handle: file handle
        :return: the structure lines
        :rtype: list
        """
        lines = []
        n = 0
        pos = file_handle.tell()
        line = file_handle.readline()
        while line:
            if STRUCTURE_DELIMITERS['mol2_file'] in line:
                if n == 0:
                    n += 1
                else:
                    file_handle.seek(pos)
                    break
            lines.append(line)
            pos = file_handle.tell()
            line = file_handle.readline()
        return lines

    @staticmethod
    def extract_sdf_structure_lines(file_handle):
        """Extract a single structure from an sdf file handle.

        :param file_handle: an open ligand sdf file handle
        :type file_handle: file handle
        :return: the structure lines
        :rtype: list
        """
        lines = []
        line = file_handle.readline()
        while line:
            lines.append(line)
            if STRUCTURE_DELIMITERS['sdf_file'] in line:
                break
            line = file_handle.readline()
        return lines

    def write_batches(self):
        """Split up the ligand_file into batches and yield them one by one as
        a generator.

        :return: The full path to .tar.gz files for individual batches.
        :rtype: Iterator[str]
        """
        tarball = None
        lines = []
        structure_count = 0
        ext = None
        source_ligandfiles = BatchMapping() if self.write_batch_mapping \
            else None

        # If the ligand_file to resume from is specified, then keep searching
        # till the ligand_file_to_resume
        if self.write_resume_log and self.resume.should_resume:
            self.resume.read_resume_log_and_build_list()

        for ligand_file, ligand_file_original_path in self.gather_files():
            logging.info('Batching %s...' % ligand_file)

            # pick the extension of the source ligand file
            ext = os.path.splitext(ligand_file)[1]

            with open(ligand_file, 'r') as ligands:
                ligand_file_structure_count = 0

                while True:
                    structure_lines = []
                    if ext == '.mol2':
                        structure_lines = \
                            LigandBatchGenerator.extract_mol2_structure_lines(
                                ligands)
                    else:
                        structure_lines = \
                            LigandBatchGenerator.extract_sdf_structure_lines(
                                ligands)

                    if not structure_lines:
                        break
                    else:
                        if self.write_resume_log and \
                                self.resume.should_resume and \
                                self.resume.exists(
                                        self.resume.filename(
                                            os.path.basename(ligand_file),
                                            ligand_file_structure_count),
                                        self.resume.filename(
                                            ligand_file_original_path,
                                            ligand_file_structure_count)):
                            # clear out the lines we already processed
                            lines.clear()
                            # increase the structure counter for this file
                            ligand_file_structure_count += 1
                            continue

                        # Write ligand to resumelog
                        if self.write_resume_log:
                            self.resume.add_ligand_to_resume_log(
                                self.resume.filename(
                                    os.path.basename(ligand_file),
                                    ligand_file_structure_count),
                                self.resume.filename(
                                    ligand_file_original_path,
                                    ligand_file_structure_count))

                        lines.extend(structure_lines)
                        ligand_file_structure_count += 1
                        structure_count += 1

                        # update batch mapping file
                        if self.write_batch_mapping:
                            source_ligandfiles.add(
                                    ligand_file_original_path,
                                    structure_count)

                    # Write the batch
                    if structure_count == self.batch_size:
                        self.batches_done += 1
                        outfile_base = f'batch_{self.batches_done:08}{ext}'
                        outfile_name = os.path.join(self.out_dir, outfile_base)
                        with open(outfile_name, 'w') as out_file:
                            out_file.writelines(lines)
                        tarball = self.tarball_batch(outfile_base,
                                                     self.protein_path,
                                                     self.cavity_path,
                                                     source_ligandfiles)
                        os.remove(outfile_name)
                        logging.info(f'Created batch of {structure_count} '
                                     f'ligands ... batch {self.batches_done}')
                        yield tarball

                        lines = []
                        structure_count = 0

            try:
                os.remove(ligand_file)
                logging.info(f'Deleting {ligand_file}')
            except OSError:
                pass

        # Any remainder of the last file that doesn't completely fill the batch
        # size also needs to be written and yielded as a final batch
        if structure_count > 0:
            self.batches_done += 1
            outfile_base = f'batch_{self.batches_done:08}{ext}'
            outfile_name = os.path.join(self.out_dir, outfile_base)
            with open(outfile_name, 'w') as out_file:
                out_file.writelines(lines)
            tarball = self.tarball_batch(outfile_base, self.protein_path,
                                         self.cavity_path, source_ligandfiles)
            os.remove(outfile_name)
            logging.info(f'Created batch of {structure_count} ligands ... '
                         f'batch {self.batches_done}')
            yield tarball

    def process_file(self, file_name):
        """Ensure that our source files are actual structure files.

        For tarballs or gzip files, extract their contents to a temporary
        directory from which they can be read and split into batches. For any
        other files, assume they are already an SDF or MOL2 file and just
        copy them over.

        :param file_name: The full path of the file to process
        :type file_name: str
        :returns: The full path to the extracted or copied file
        :rtype: Iterator[str]
        """
        ext = os.path.splitext(file_name)[1]

        if file_name.endswith('.tar.gz') or ext == '.tar':
            # Source file is a tarball so we want to extract all the files
            # from it.
            with tarfile.open(file_name, 'r') as tar:
                for member in tar.getmembers():
                    stored_file = os.path.join(self.tempdir,
                                               os.path.basename(member.name))
                    file_stream = tar.extractfile(member)
                    with open(stored_file, 'wb') as out_file:
                        out_file.write(file_stream.read())
                    yield stored_file

        elif ext == '.gz':
            # Source file is not a tarball, but gzipped - strip the .gz
            # extension off
            file_basename = os.path.splitext(os.path.basename(file_name))[0]
            stored_file = os.path.join(self.tempdir, file_basename)
            with gzip.open(file_name, 'r') as gzfile:
                with open(stored_file, 'wb') as out_file:
                    try:
                        out_file.write(gzfile.read())
                    except EOFError:
                        logging.error(f'Possible corrupt file at {file_name}. '
                                      'Will not be batched.')
            yield stored_file
        elif ext in ['.sd', '.sdf', '.mol2']:
            # We support sd, sdf or mol2 extensions
            # Source file is not a gzip or tarball, assume it's a bare
            # structure file
            shutil.copy(file_name, self.tempdir)
            yield os.path.join(self.tempdir, os.path.basename(file_name))

    def gather_files(self, ligand_path=None):
        """Gather source files from ligand_path.

        There are two levels of structures here.
        1. ligand_path can either be a file or a directory. If a directory,
           all files in all subdirectories are processed.
        2. For each file found (one file if ligand_path is a file, or all files
           in the directory structure otherwise), it could either be an actual
           structure file (mol2 or sdf) or a zipped up structure file (gz) or
           a tarball of structures files. This is processed in process_file.

        For each structure file found or extracted, we yield a tuple of the
        structure file path (copied or extracted to the tempdir) and the
        original file it's copied or extracted from (ie. ligand_path or a file
        in its directory structure if it's a directory).

        The optional ligand_path can be used for testing.

        :param ligand_path: Provide alternative ligand path, if desired
        :type ligand_path: str, optional

        :returns: A tuple of structure file path and original file path
        :rtype: Iterator[tuple]
        """
        file_path = ligand_path if ligand_path else self.ligand_path
        if os.path.isdir(file_path):
            for root, directories, files in os.walk(file_path):
                for f in sorted(files, key=lambda x: x, reverse=False):
                    for file_name in self.process_file(os.path.join(root, f)):
                        yield file_name, os.path.join(root, f)
        elif os.path.isfile(file_path):
            for file_name in self.process_file(file_path):
                yield file_name, file_path

    def cleanup(self):
        """Clean up temporary files"""
        shutil.rmtree(self.tempdir)
        shutil.rmtree(self.out_dir)

    def batches(self, cleanup=True):
        """Generate batches from the source files.

        Loop over this with 'for batch in LigandBatchGenerator().batches()'
        to retrieve all batches for all the source files given.

        :return: Full path to .tar.gz files of a full set of files for docking.
        :rtype: Iterator[str]
        """

        for batch in self.write_batches():
            yield batch
            if self.total_batches:
                if self.batches_done >= self.total_batches:
                    break

        if cleanup:
            self.cleanup()

        # close the resume log once we have completed processing batches
        if self.resume:
            self.resume.close()


class CollectResult():
    """Collect gold docking results into a single place"""
    def __init__(self, results_dir, jobids=[], slurm_jobid=None,
                 num_top_results=1000000):
        """Initiate CollectResult

        :param results_dir: Location of the GOLD docking results to collect
        :type results_dir: str
        :param jobids: The list of job IDs read from jobid.txt
        :type jobids: list of int, optional
        :param slurm_jobid: The job ID as returned by sbatch
        :type slurm_jobid: int, optional
        :param num_top_results: Number of top best ranking results to save,
            defaults to 1000000
        :type num_top_results: int, optional


        """
        self.slurm_jobid = slurm_jobid
        self.jobids = jobids
        self.results_dir = results_dir

        # best ranking settings
        # Number of top results to save
        self.num_top_results = num_top_results

        self.batches = 0
        self.merged_bestranking_file = None
        self.logger = create_logger()

    def merge_results_for_jobid(self, merged_output_dir, jobid):
        self.logger.info(
            f'Hermes results collection started for Job ID {jobid}...')
        results_dir = Path(self.results_dir) / str(jobid)
        outtars = Path(results_dir).glob(f'output_{jobid}_*')
        for outtar in outtars:
            tt = tarfile.open(outtar, 'r')
            for member in tt.getmembers():
                if member.name == 'gold_protein.mol2' \
                        or 'gold_soln_' in member.name:
                    tt.extract(member, str(merged_output_dir))
        self.logger.info(
            f'Hermes results collection completed for Job ID {jobid}')

    def merge_hermes_files(self, merged_dir):
        """Merge the results so they can be visualized by Hermes

        :param merged_dir: The directory of the merged results.
        :type merged_dir: str
        """
        Path(merged_dir).mkdir(parents=True, exist_ok=True)

        if self.slurm_jobid == 'all':
            for jobid in self.jobids:
                self.merge_results_for_jobid(merged_dir, jobid)
        else:
            self.merge_results_for_jobid(merged_dir, self.slurm_jobid)

    def write_bestranking_file(self, ranking_file):
        """Write the merged bestranking file to disk"""
        try:
            with ranking_file.open(mode="w") as fh:
                fh.write('\n'.join(self.results) + '\n')
            logging.info(f'Writing results: {len(self.results)}')
        except FileNotFoundError:
            logging.info('No results to write')

    def merge_bestranking_results(self, new_result):
        """Merge a bestranking file content to existing sorted results.

        :param new_result: The content of a bestranking file to merge
        :type new_result: str
        """
        def sort_by_score(line):
            if line:
                return float(line.split(None, 1)[0])
            else:
                return 0.0

        new_results = [line for line in new_result.splitlines()
                       if line.strip() and not line.startswith('#')]
        merged_lines = sorted(self.results + new_results,
                              key=sort_by_score,
                              reverse=True)
        self.results = merged_lines[:self.num_top_results]

    def read_existing_result(self, result_file):
        if result_file.is_file():
            with result_file.open() as fh:
                logging.info('Reading from disk existing results')
                self.results = fh.read().splitlines()
        else:
            self.results = []

    def merge_bestranking_for_jobid(self, jobid):
        self.logger.info(
            f'Bestranking file merging started for Job ID {jobid}...')
        results_dir = Path(self.results_dir) / str(jobid)
        outtars = Path(results_dir).glob(f'output_{jobid}_*')
        for outtar in outtars:
            tt = tarfile.open(outtar, 'r')
            for member in tt.getmembers():
                if member.name == BESTRANKING_FILENAME:
                    self.merge_bestranking_results(
                        tt.extractfile(member).read().decode())
        self.logger.info(
            f'Bestranking file merging completed for Job ID {jobid}')

    def merge_bestranking(self, merged_dir=''):
        """Merge the bestranking file

        :param merged_dir: The directory of the merged results.
        :type merged_dir: str
        """
        if merged_dir == '':
            self.merged_bestranking_file = Path(BESTRANKING_FILENAME)
        else:
            merged_dir.mkdir(parents=True, exist_ok=True)
            self.merged_bestranking_file = merged_dir / BESTRANKING_FILENAME

        # If a results file exists, take into account existing results.
        self.read_existing_result(self.merged_bestranking_file)

        if self.slurm_jobid == 'all':
            for jobid in self.jobids:
                self.merge_bestranking_for_jobid(jobid)
        else:
            self.merge_bestranking_for_jobid(self.slurm_jobid)

        self.write_bestranking_file(self.merged_bestranking_file)
