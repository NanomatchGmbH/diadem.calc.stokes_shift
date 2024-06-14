# !/usr/bin/env python3
"""
Every component of the workflow has this structure:
get_output
prepare: run some python commands, or commands
run command [executable]
check_output
check_files
copy_out_to_out
copy files to diadem_files
"""
import glob
import os
import pathlib
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any

import psutil
import structlog
import yaml

from utils.build_command_from_yml import build_command
from utils.change_dictionary import copy_with_changes  # todo: rename
from utils.logging_config import configure_logging
from utils.subprocess_functions import run_command
from utils.deposit_functions import setup_working_directory, check_and_extract_deposit_restart, \
    add_periodic_copies_deposit, create_deposit_restart_zip, handle_deposit_working_dir_cleanup, run_analysis, \
    append_settings
from utils.result import get_result_from
from utils.context_managers import ChangeDirectory
from utils.lightforge_functions import set_carrier_type
from utils.quantumpatch_functions import rename_file

debug = False
opt_tmpl = "/opt/tmpl"

# Create a logger
configure_logging()
logger = structlog.get_logger()


def list_directory_contents(path='.'):
    """
    List the contents of a directory and log it.
    """
    try:
        contents = list(pathlib.Path(path).iterdir())
        for item in contents:
            logger.info(f"Found item: {item.name}", item_type="directory" if item.is_dir() else "file",
                        size=item.stat().st_size)
        return contents
    except Exception as e:
        logger.error("Failed to list directory contents", error=str(e))
        raise


def list_installed_micromamba_packages():
    try:
        result = subprocess.run(['micromamba', 'list'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                encoding='utf8')
        installed_packages = result.stdout
        logger.info("Installed packages:\n" + installed_packages)
    except subprocess.CalledProcessError as e:
        logger.error("Failed to list installed packages", error=str(e))
        raise


def check_required_output_files_exist(filepaths, description="file"):
    """
    Check if a file or list of files exists in the current working directory and log a critical error if any are missing.
    Raise a FileNotFoundError if any file is not found.
    Treat filenames with wildcards (e.g., "Delta_*.png") by finding all files that match the pattern.
    """
    if isinstance(filepaths, (str, pathlib.Path)):
        filepaths = [filepaths]

    cwd = pathlib.Path.cwd()
    missing_files = []

    for pattern in filepaths:
        matched_files = glob.glob(str(cwd / pattern))
        if not matched_files:
            missing_files.append(str(pattern))

    if missing_files:
        logger.critical(f"Required {description}(s) missing in current working directory: {', '.join(missing_files)}")
        raise FileNotFoundError(
            f"Required {description}(s) missing in current working directory: {', '.join(missing_files)}")


def create_output_directory_and_copy_files(required_files, output_dir='out'):
    """
    Create an output directory and copy the required files into it.

    Parameters:
    required_files (list): List of file paths to be copied, with support for wildcards.
    output_dir (str): Name of the output directory.
    """
    # Create the output directory using pathlib
    output_dir_path = pathlib.Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Copy the required files to the output directory
    for pattern in required_files:
        # Expand the wildcard pattern to match files
        matched_files = glob.glob(pattern)
        if not matched_files:
            logger.critical(f"No files matched the pattern: {pattern}")
            raise FileNotFoundError(f"No files matched the pattern: {pattern}")
        for file in matched_files:
            file_path = pathlib.Path(file)
            shutil.copy(file_path, output_dir_path)

    # Return the absolute path of the output directory
    return str(output_dir_path.resolve())


def fetch_output_from_previous_executable(previous_executable, sub_dir='out'):
    """
    Copy files from the previous executable's output directory to the current working directory.

    Parameters:
    previous_executable (str): Name of the previous executable directory.
    sub_dir (str): Subdirectory inside the previous executable's directory to copy files from.
    """
    prev_output_dir = pathlib.Path('../') / previous_executable / sub_dir
    current_dir = pathlib.Path.cwd()

    for file in prev_output_dir.iterdir():
        if file.is_file():
            shutil.copy(file, current_dir)


def generate_hostfile(num_cores: int, output_file: str):
    """
    Generates a universal hostfile for SLURM by determining the node name dynamically.

    Parameters:
    num_cores (int): Number of physical cores/processes.
    output_file (str): Output file path for the hostfile.
    """
    # Get the node name (hostname)
    node_name = socket.gethostname()

    # Write the node name num_cores times to the output file
    with open(output_file, 'w') as file:
        for _ in range(num_cores):
            file.write(f"{node_name}\n")


def find_executable_path(executable_name):
    """
    Find the path of an executable by its name.

    Parameters:
    executable_name (str): The name of the executable to find.

    Returns:
    str: The path of the executable.

    Raises:
    FileNotFoundError: If the executable is not found.
    """
    try:
        result = subprocess.run(['which', executable_name], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                encoding='utf8')
        executable_path = result.stdout.strip()
        logger.info(f"Found {executable_name} at {executable_path}")
        return executable_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to find {executable_name}", error=str(e))
        raise FileNotFoundError(f"{executable_name} not found") from e


class Executable(Enum):
    XTB = 'xtb'
    QPPARAMETRIZER = 'QPParametrizer'
    DIHEDRAL_PARAMETRIZER = 'DihedralParametrizer'
    QUANTUMPATCH = 'QuantumPatch'
    DEPOSIT = 'Deposit'
    LIGHTFORGE_HOLE = 'lightforge_hole'
    LIGHTFORGE_ELECTRON = 'lightforge_electron'


# Define the WorkflowConfig dataclass with an extended constructor
@dataclass
class WorkflowConfig:
    """
    data associated with every Executable is all here.
    By default, the data is constructed from files in: /opt/tmpl/<Executable.value>/
    """
    required_files: Dict[Executable, List[str]] = field(default_factory=dict)
    files: Dict[Executable, List[str]] = field(default_factory=dict)
    debugFiles: Dict[Executable, List[str]] = field(default_factory=dict)
    errorStageOut: Dict[Executable, List[str]] = field(default_factory=dict)
    optionalFiles: Dict[Executable, List[str]] = field(default_factory=dict)
    result: Dict[Executable, Dict] = field(default_factory=dict)

    @classmethod
    def from_files(cls, tmpl_folder: str):
        required_files = cls._read_txt_files(tmpl_folder, 'required_files.txt')
        files = cls._read_txt_files(tmpl_folder, 'files.txt')
        operationaFiles = 'operationFiles'
        debugFiles = cls._read_txt_files(tmpl_folder, f'{operationaFiles}/debugFiles')
        errorStageOut = cls._read_txt_files(tmpl_folder, f'{operationaFiles}/errorStageout')
        optionalFiles = cls._read_txt_files(tmpl_folder, f'{operationaFiles}/optionalFiles')
        result = cls._read_yaml_files(tmpl_folder, 'result.yml')
        return cls(required_files=required_files, files=files, debugFiles=debugFiles, errorStageOut=errorStageOut,
                   optionalFiles=optionalFiles, result=result)

    @staticmethod
    def _read_txt_files(base_directory: str, file_name: str) -> Dict[Executable, List[str]]:
        files_dict = {}
        for executable in Executable:
            file_path = pathlib.Path(base_directory) / executable.value / file_name
            if file_path.is_file():
                with open(file_path, 'r') as file:
                    files_dict[executable] = [line.strip() for line in file.readlines()]
            else:
                files_dict[executable] = []
        return files_dict

    @staticmethod
    def _read_yaml_files(base_directory: str, file_name: str) -> Dict[Executable, Dict[str, Any]]:
        yaml_dict = {}
        for executable in Executable:
            yaml_path = pathlib.Path(base_directory) / executable.value / file_name
            if yaml_path.is_file():
                with open(yaml_path, 'r') as file:
                    yaml_dict[executable] = yaml.safe_load(file)
            else:
                yaml_dict[executable] = {}
        return yaml_dict


def zip_files_or_file_patterns(debug_files, output_zip_path):
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_pattern in debug_files:
            for file in glob.glob(file_pattern, recursive=True):
                if os.path.isfile(file):
                    zipf.write(file, os.path.relpath(file, start=os.path.dirname(file_pattern)))
                elif os.path.isdir(file):
                    for root, dirs, files in os.walk(file):
                        for file_name in files:
                            file_path = os.path.join(root, file_name)
                            zipf.write(file_path, os.path.relpath(file_path, start=os.path.dirname(file_pattern)))
    return output_zip_path


def distribute_files(executable, wf_config: WorkflowConfig, diadem_files_output_dir, debug=False, error_happened=False):
    """
    Required files are the files required for the next step of the workflow.
    They go to out folder and later copied over to the simulation folder of the next woorkflow step.
    Other type of files are specified in the DIADEM documentation.
    """
    # Process required files (copy to output directory)
    required_files = wf_config.required_files.get(executable)
    if required_files:
        if not error_happened:
            check_required_output_files_exist(required_files)
        create_output_directory_and_copy_files(required_files, 'out')

    # Process diadem files (copy to output directory)
    # diadem files are simply "files" in terms of DIADEM.
    diadem_files = wf_config.files.get(executable)
    if diadem_files:
        if not error_happened:
            check_required_output_files_exist(diadem_files)
        create_output_directory_and_copy_files(diadem_files, diadem_files_output_dir)
    # Process debug files (zip one level higher)
    if debug:
        debug_files = wf_config.debugFiles.get(executable)
        if debug_files:
            check_required_output_files_exist(debug_files)
            zip_files_or_file_patterns(debug_files, f'../{executable.value}_debugFiles.zip')

    # Process optional files (zip one level higher)
    optional_files = wf_config.optionalFiles.get(executable)
    if optional_files:
        zip_files_or_file_patterns(optional_files, f'../{executable.value}_optionalFiles.zip')

    # Process errorStageOut files (zip one level higher)
    if error_happened:
        error_stageOut_files = wf_config.errorStageOut.get(executable)
        if error_stageOut_files:
            zip_files_or_file_patterns(error_stageOut_files, f'../{executable.value}_errorStageOut.zip')


########################################################################################################################


if debug:
    logger.info(f"{os.getcwd()=}")
    list_installed_micromamba_packages()
    env_vars = dict(os.environ)
    logger.info("Environment variables at start", environment=env_vars)
    # Adding context for some critical environment variables
    logger.info("Active Conda environment", conda_env=env_vars.get('CONDA_DEFAULT_ENV', 'N/A'))
    logger.info("Number of OpenMP threads", omp_threads=env_vars.get('OMP_NUM_THREADS', 'N/A'))
    logger.info("CPU binding policy", slurm_cpu_bind=env_vars.get('SLURM_CPU_BIND', 'N/A'))

    # Print environment variables for debugging
    logger.info("NMMPIARGS", NMMPIARGS=os.environ.get('NMMPIARGS'))
    logger.info("ENVCOMMAND", ENVCOMMAND=os.environ.get('ENVCOMMAND'))
    logger.info("HOSTFILE", HOSTFILE=os.environ.get('HOSTFILE'))

try:
    with open("molecule.yml", 'rt') as infile:
        moldict = yaml.safe_load(infile)
    logger.info("Loaded molecule.yml", molecule=moldict)
except Exception as e:
    logger.error("Failed to load molecule.yml", error=str(e))
    raise

try:
    with open("calculator.yml", 'rt') as infile:
        calcdict = yaml.safe_load(infile)
    logger.info("Loaded calculator.yml", calculator=calcdict)
except Exception as e:
    logger.error("Failed to load calculator.yml", error=str(e))
    raise

# The engine, which was instantiated, needs to provide "provides" (e.g HOMO and LUMO)
provides = calcdict["provides"]
changes = calcdict['specification']
global_calc_settings = changes.get(
    'global')  # contains things which are general to all specifications, in this case to all tools. Like number of cpus.
files = calcdict['files']

inchi = moldict["inchi"]
inchiKey = moldict["inchiKey"]

wf_config = WorkflowConfig.from_files(opt_tmpl)

for executable in Executable:
    logger.info(f"Specified files for {executable.value}:")
    logger.info(required_files={executable.value: list(wf_config.required_files.get(executable))})
    logger.info(files={executable.value: list(wf_config.files.get(executable))})
    # logger.info(debugFiles={executable.value: list(wf_config.debugFiles.get(executable))})
    logger.info(errorStageOut={executable.value: list(wf_config.errorStageOut.get(executable))})
    logger.info(optionalFiles={executable.value: list(wf_config.optionalFiles.get(executable))})
    logger.info(result={executable.value: list(wf_config.result.get(executable))})


#####

"""
Ensure that the script knows where to locate the files specified in the calculator. Otherwise, it makes no sense to proceed.
This block performs a critical check to ensure consistency between the files required by the calculator and the files produced by various executables.

The files specified in the calculator must match the BASE names of the files listed in the files.txt files for each executable. This is crucial because:
1. It establishes a clear relationship between the files and the executables that produce them.
2. The calculator specifies files by their base names, while the files listed in /opt/tmpl/<Exe>/files.txt include the relative paths from the current executable's directory to the file.

Example:
If the calculator specifies a file as 'output_file.txt', the corresponding entry in /opt/tmpl/<Exe>/files.txt might be '/path/to/output_file.txt'.

This block compares the sets of files to ensure that:
1. Every file required by the calculator has a corresponding entry in the files produced by the executables.
2. Every file listed in the files.txt files has a corresponding entry in the calculator.

If there are discrepancies, the script logs the specific missing or extra files and terminates execution to prevent further errors.
"""


def files_names_with_specified_locations(fls):
    file_names = []
    for paths in fls.values():
        for path in paths:
            file_name = pathlib.Path(path).name
            file_names.append(file_name)
    return file_names


files_from_locations = files_names_with_specified_locations(wf_config.files)
files_from_calculator = files

if set(files_from_locations) != set(files_from_calculator):
    missing_files = set(files_from_calculator) - set(files_from_locations)
    extra_files = set(files_from_locations) - set(files_from_calculator)

    logger.critical(f"The calculator needs to know where to look for the following files: {files_from_calculator}. "
                    f"However, paths are only specified for the following files: {files_from_locations}. ")

    if missing_files:
        logger.critical(
            f"Missing files that are specified in the calculator but not in the file locations: {missing_files}")

    if extra_files:
        logger.critical(f"Extra files that have paths specified but are not required by the calculator: {extra_files}")

    sys.exit("Exiting due to mismatched files.")
else:
    logger.info("Sanity Check Successful: The Calculator knows paths to the [diadem] files that have to be returned.")

# <--


folder_name = 'diadem_files'
pathlib.Path(folder_name).mkdir(parents=True, exist_ok=True)
diadem_dir_abs_path = pathlib.Path(folder_name).resolve()
logger.info(f" Folder to copy specified in the Calculator files will be copied to {diadem_dir_abs_path}.")

resultdict = {inchiKey: {}}  # result that will be processed by front-end.

logger.info(" ================================= Workflow starts . . . ================================================")

# 0. ######################
executable = Executable.XTB
###########################

try:
    with ChangeDirectory(executable.value):
        # 1 .PREOPTIMIZATION WITH NO NM SOFTWARE
        # we generate a bad 3d structure. Plan below:
        # mol.inchi -[obabel]-> mol.xyz ->[xtb]-> xtbout.xyz -[obabel]-> input_molecule.mol2
        mol_inchi = 'mol.inchi'
        with open(mol_inchi, 'w') as outfile:
            outfile.write(f"{inchi}\n")

        logger.info("Generate 3D conformer of the molecule . . .")
        initial_conformer_xyz = 'mol.xyz'
        command = f"obabel -i inchi {mol_inchi} -o xyz -O {initial_conformer_xyz} --gen3d"
        run_command(command)
        required_files = [initial_conformer_xyz]
        check_required_output_files_exist(initial_conformer_xyz)

        # optimize using xtb from xtb, not from parametrizer.
        # we optimize the bad 3d structure [initial_conformer]
        logger.info("xtb optimization of 3D conformer of the molecule . . .")
        command = f"{executable.value} {initial_conformer_xyz} --opt"  # outputs xtbout.xyz
        run_command(command)
        xtb_preoptimized_xyz = 'xtbopt.xyz'
        required_files = [xtb_preoptimized_xyz]
        check_required_output_files_exist(required_files)

        logger.info("Transfer xyz to mol2 . . .")
        xtb_preoprimized_mol2 = 'input_molecule.mol2'
        command = f"obabel -i xyz {xtb_preoptimized_xyz} -o mol2 -O {xtb_preoprimized_mol2}"
        run_command(command)

        distribute_files(executable, wf_config, diadem_dir_abs_path, debug=debug)
except Exception as e:
    logger.error(f"An error occurred during {executable.value} processing: {e}")
    distribute_files(executable, wf_config, diadem_dir_abs_path, error_happened=True, debug=debug)
    sys.exit(1)

# 1 -> 2
previous_executable = executable  #

# 2 ##################################
executable = executable.QPPARAMETRIZER
######################################


try:
    with ChangeDirectory(executable.value):
        # todo: copy the output directory may be a part of the context manager?

        fetch_output_from_previous_executable(previous_executable.value)

        command = f"{executable.value}"
        source_path = f'{opt_tmpl}/{executable.value}/parametrizer_settings.yml'  # template has the name of the executable
        destination_path = pathlib.Path.cwd() / 'parametrizer_settings.yml'  # Current directory
        copy_with_changes(source_path, changes[executable.value], destination_path)

        run_command(command)

        distribute_files(executable, wf_config, diadem_dir_abs_path, debug=debug)

        # result
        local_resultdict = wf_config.result.get(executable)
        get_result_from.QPParametrizer(local_resultdict, 'mol_data.yml')
        resultdict[inchiKey].update(local_resultdict)
        with open("result.yml", 'wt') as outfile:
            yaml.dump(local_resultdict,
                      outfile)  # we save the result locally in QPP folder in case the script will crash on a later stage.
except Exception as e:
    logger.error(f"An error occurred during {executable.value} processing: {e}")
    distribute_files(executable, wf_config, diadem_dir_abs_path, error_happened=True, debug=debug)
    sys.exit(1)

# 2->3
previous_executable = executable

# 3. ########################################
executable = Executable.DIHEDRAL_PARAMETRIZER
#############################################


try:
    with ChangeDirectory(executable.value):
        fetch_output_from_previous_executable(previous_executable.value)

        # 3.0. Prepare HOSTFILE
        all_avail_physical_cpus = psutil.cpu_count(logical=False)
        numcpus = global_calc_settings.get('ncpus', all_avail_physical_cpus)
        hostfile_name = os.environ.get('HOSTFILE', 'hostfile.txt')  # it might be set from above.
        os.environ['HOSTFILE'] = hostfile_name
        generate_hostfile(numcpus, hostfile_name)

        # Ensure DEPTOOLS is set in the environment todo needed?
        dep_tools = os.environ.get('DEPTOOLS')
        if not dep_tools:
            logger.error("DEPTOOLS environment variable is not set")
            raise EnvironmentError("DEPTOOLS environment variable is not set")

        # Add dihedral angles
        output_molecule_mol2_from_parametrizer = 'output_molecule.mol2'
        molecule_spf_from_parametrizer = 'molecule.spf'

        command = f"{dep_tools}/add_dihedral_angles.sh {output_molecule_mol2_from_parametrizer} {molecule_spf_from_parametrizer}"
        run_command(command)

        # Zip files
        command = f"zip report.zip {output_molecule_mol2_from_parametrizer} molecule.pdb {molecule_spf_from_parametrizer}"
        run_command(command)

        # Append mol_data.yml to output_dict.yml ### artem: why do we need this at all?
        # command = "cat mol_data.yml >> output_dict.yml"  # I did not want to make this because this is bash-specific.

        # Convert mol2 to svg
        command = "obabel -imol2 output_molecule.mol2 -osvg"
        run_command(command, output_file="output_molecule.svg")

        source_path = f'{opt_tmpl}/DihedralParametrizer/dhp_settings.yml'
        destination_path = './dhp_settings.yml'  # Current directory

        copy_with_changes(source_path, changes["DihedralParametrizer"], destination_path)

        output_molecule_pdb_after_add_dyhedrals = "molecule.pdb"
        output_molecule_spf_after_add_dyhedrals = "molecule.spf"
        dhp_settings = "dhp_settings.yml"

        required_files = [output_molecule_pdb_after_add_dyhedrals, output_molecule_spf_after_add_dyhedrals,
                          dhp_settings]
        check_required_output_files_exist(required_files)

        executable_path = find_executable_path(executable.value)

        # Run DihedralParametrizer with MPI
        command = f"mpirun --bind-to none $NMMPIARGS $ENVCOMMAND --hostfile $HOSTFILE --mca btl self,vader,tcp python -m mpi4py {executable_path} ./dhp_settings.yml"
        run_command(command, use_shell=True)

        molecule_pdb_from_DHP_as_generated = 'molecule.pdb'
        molecule_spf_from_DHP_as_generated = 'dihedral_forcefield.spf'
        required_files = [molecule_pdb_from_DHP_as_generated, molecule_spf_from_DHP_as_generated]
        check_required_output_files_exist(required_files)

        molecule_pdb_from_DHP = 'molecule_0.pdb'  # names recognized by Deposit as in WANO. Do not want to use others here.
        molecule_spf_from_DHP = 'molecule_0.spf'
        shutil.move(molecule_pdb_from_DHP_as_generated, molecule_pdb_from_DHP)
        shutil.move(molecule_spf_from_DHP_as_generated, molecule_spf_from_DHP)

        distribute_files(executable, wf_config, diadem_dir_abs_path, debug=debug)

        # no result to go into result.yml
except Exception as e:
    logger.error(f"An error occurred during {executable.value} processing: {e}")
    distribute_files(executable, wf_config, diadem_dir_abs_path, error_happened=True, debug=debug)
    sys.exit(1)

# 3->4
previous_executable = executable

# 4.###########################
executable = Executable.DEPOSIT
###############################

try:
    with ChangeDirectory(executable.value):
        fetch_output_from_previous_executable(previous_executable.value)

        source_path = f'{opt_tmpl}/{executable.value}/deposit_cargs.yml'  # command line args of Deposit as dictionary
        destination_path = pathlib.Path.cwd() / 'deposit_cargs.yml'

        copy_with_changes(source_path, changes[executable.value], destination_path)

        # Generate a UUID in Python
        # todo: do we need to cd and so on??? for consistency??
        # todo: what happens for Deposit: not only we create Deposit direcory and make sims there, we also create or use some kind of SCRATCH directory, which will not be there on Azure. Resolve?
        generated_uuid = str(uuid.uuid4())
        logger.info(f"Generated UUID: {generated_uuid}")

        # Set necessary environment variables
        env_vars = os.environ.copy()
        env_vars['GENERATED_UUID'] = generated_uuid

        # script_path = 'deposit_init.sh'  # the way deposit run is different
        # run_shell_script(script_path, env_vars)

        # deposit_init commands -->
        current_dir, working_dir = setup_working_directory()  # this will copy things from the current to the working dir and change to it silently!!
        check_and_extract_deposit_restart()  # not used at the moment. left to allow for script extension.

        command = build_command(destination_path)  # this is the Deposit commands with appropriate command line args
        run_command(command)

        required_files = ['structure.cml']
        check_required_output_files_exist(required_files)

        command = "obabel -i cml structure.cml -o mol2 -O structure.mol2"
        run_command(command)

        add_periodic_copies_deposit()
        create_deposit_restart_zip()
        handle_deposit_working_dir_cleanup(current_dir,
                                           working_dir)  # this will first copy everything from work to data (current dir) and then clean up the data dir. Insane.
        run_analysis()
        append_settings()
        #
        # <-- deposit_init commands
        distribute_files(executable, wf_config, diadem_dir_abs_path, debug=debug)

        # result -->
        local_resultdict = wf_config.result.get(executable)
        get_result_from.Deposit(local_resultdict, 'DensityAnalysis.out')
        resultdict[inchiKey].update(local_resultdict)
        with open("result.yml", 'wt') as outfile:
            yaml.dump(local_resultdict, outfile)
        # <-- result
except Exception as e:
    logger.error(f"An error occurred during {executable.value} processing: {e}")
    distribute_files(executable, wf_config, diadem_dir_abs_path, error_happened=True, debug=debug)
    sys.exit(1)

# 4->5
previous_executable = executable

# 5 ################################
executable = Executable.QUANTUMPATCH
###################################

try:
    with ChangeDirectory(executable.value):
        fetch_output_from_previous_executable(previous_executable.value)

        source_path = f'{opt_tmpl}/{executable.value}/settings_ng.yml'
        destination_path = pathlib.Path.cwd() / 'settings_ng.yml'
        copy_with_changes(source_path, changes[executable.value], destination_path)

        if 'SCRATCH' not in os.environ:
            # Generate a random directory inside the current directory which will serve as a SCRATCH
            current_dir = os.getcwd()
            scratch_dir = os.path.join(current_dir, "qp_scratch_" + next(tempfile._get_candidate_names()))
            # Ensure the directory exists
            os.makedirs(scratch_dir, exist_ok=True)
            # Set the SCRATCH environment variable
            os.environ['SCRATCH'] = scratch_dir

        logger.info(f"SCRATCH for QuantumPatch is set to: {os.environ['SCRATCH']}")

        # 5.1. RUN QP
        # the only necessary input for QP: structure or structurePBC is in the current folder.
        executable_path = find_executable_path(executable.value)

        os.environ['OMP_NUM_THREADS'] = '1'
        all_avail_physical_cpus = psutil.cpu_count(logical=False)
        n_cpus_for_qp = changes.get('global', {}).get('ncpus', all_avail_physical_cpus)

        command = f'mpirun --bind-to none -np {n_cpus_for_qp} $NMMPIARGS $ENVCOMMAND --mca btl self,vader,tcp python -m mpi4py {executable_path}'
        run_command(command, use_shell=True)

        required_files = ['Analysis/files_for_kmc/files_for_kmc.zip']  # todo maybe check individual files.
        check_required_output_files_exist(required_files)

        # 5.2. Prepare input for LF
        # Define the directory to be zipped and the name of the zip file: needed for lightforge
        directory_to_zip = "Analysis"
        required_files = wf_config.required_files.get(executable)
        zipped_analysis_folder = "QP_output_0.zip"

        # Create a zip from Analysis of QP.
        with zipfile.ZipFile(zipped_analysis_folder, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through the directory
            for root, dirs, files in os.walk(directory_to_zip):
                for file in files:
                    # Create the complete filepath of the file in the zip
                    file_path = os.path.join(root, file)
                    # Add the file to the zip file, preserving the directory structure
                    zipf.write(file_path, os.path.relpath(file_path, directory_to_zip))

        logger.info(
            f"Directory '{directory_to_zip}' zipped into '{zipped_analysis_folder}' successfully. This will be the LF input.")

        # workaround deltaE_*.png --> deltaE.png:
        rename_file('Analysis/energy/DeltaE*.png', 'DeltaE.png')
        
        distribute_files(executable, wf_config, diadem_dir_abs_path, debug=debug)
except Exception as e:
    logger.error(f"An error occurred during {executable.value} processing: {e}")
    distribute_files(executable, wf_config, diadem_dir_abs_path, error_happened=True, debug=debug)
    sys.exit(1)

# 5->6
previous_executable = executable


# 6. ##########################################################################
for executable in [Executable.LIGHTFORGE_HOLE, Executable.LIGHTFORGE_ELECTRON]:
###############################################################################
    try:
        with ChangeDirectory(executable.value):
            fetch_output_from_previous_executable(previous_executable.value)
            fetch_output_from_previous_executable(
                Executable.DIHEDRAL_PARAMETRIZER.value)  # yes, files from twp previous tools

            source_path = f'{opt_tmpl}/{executable.value}/settings'  # settings specific to hole/electron
            destination_path = pathlib.Path.cwd() / 'settings'
            copy_with_changes(source_path, changes[executable.value], destination_path)

            executable_path = find_executable_path(executable.value.split('_')[0])  # returns simply lightforge for both hole and electron.
            carrier_type = executable.value.split('_')[1]  # hole or electron

            os.environ['OMP_NUM_THREADS'] = '1'
            all_avail_physical_cpus = psutil.cpu_count(logical=False)
            n_cpus_for_lf = changes.get('global', {}).get('ncpus', all_avail_physical_cpus)
            command = f'mpirun -x OMP_NUM_THREADS --bind-to none -n {n_cpus_for_lf} --mca btl self,vader,tcp python -m mpi4py {executable_path} -s settings'
            run_command(command, use_shell=True)

            # result -->
            local_resultdict = wf_config.result.get(executable)
            get_result_from.lightforge(local_resultdict,
                                       'results/experiments/current_characteristics/mobilities_all_fields.dat', 'settings',
                                       hole_or_electron=carrier_type)

            # the side-effect of the get_result_from.lighforge is creating file mobility_vs_sqrt_field_<hole/electron>.png which will be copied as file to the front-end!!!
            resultdict[inchiKey].update(local_resultdict)
            with open("result.yml", 'wt') as outfile:  # this dict is inside the lightforge simulation folder.
                yaml.dump(local_resultdict, outfile)
            # <-- result

            distribute_files(executable, wf_config, diadem_dir_abs_path)
    except Exception as e:
        logger.error(f"An error occurred during {executable.value} processing: {e}")
        distribute_files(executable, wf_config, diadem_dir_abs_path, error_happened=True, debug=debug)
        sys.exit(1)

# resultdict will be filled in after every workflow step.
# if the workflow succeed, resultdict is complete.

logger.info("Listing directory contents at the end")
list_directory_contents()

with open("result.yml", 'wt') as outfile:
    yaml.dump(resultdict, outfile)

sys.exit(0)
