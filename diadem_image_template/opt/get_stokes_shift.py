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
from typing import Dict, List, Any, Union

import psutil
import structlog
import yaml

from utils.build_command_from_yml import build_command
from utils.change_dictionary import copy_with_changes  # todo: rename
from utils.logging_config import configure_logging
from utils.subprocess_functions import run_command
from utils.result import get_result_from
from utils.context_managers import ChangeDirectory

debug = False
opt_tmpl = "/opt/tmpl"

# Create a logger
configure_logging()
logger = structlog.get_logger()


def modify_yaml_file(destination_path):
    """
    ad hoc function to set ncpus for Deposit to 16. For some reason, it was used in production. Remove if not needed for a while!
    """
    with open(destination_path, 'r') as fid:
        deposit_cargs_dict = yaml.safe_load(fid)

    deposit_cargs_dict['machineparams']['ncpu'] = 16

    with open(destination_path, 'w') as fid:
        yaml.safe_dump(deposit_cargs_dict, fid)

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
    QPPARAMETRIZER_S0_opt = 'QPParametrizer_S0_opt'
    QPPARAMETRIZER_S1_opt = 'QPParametrizer_S1_opt'
    QPPARAMETRIZER_absorbtion = 'QPParametrizer_absorbtion'
    QPPARAMETRIZER_emission = 'QPParametrizer_emission'


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

def stop_workflow_after_module(stop_after_module, resultdict: Dict, executable: Executable, logger, is_last_module=False):
    """
    Checks if the stop condition is met and either stops execution or proceeds with the workflow.
    Example: stop_after_value == Deposit --> results.yml written, script ends.

    Parameters:
    - stop_after_module: Name of the module (e.g. 'Deposit') after which the workflow is stopped.
    - resultdict: The result dictionary written at the end of the script.
    - executable: The current executable (e.g. Executable.DEPOSIT).
    - logger: Logger instance for logging.
    - is_last_module: Boolean indicating if the current module is the last in the workflow.
    """
    if stop_after_module == executable.value or is_last_module:
        with open("result.yml", 'wt') as outfile:
            yaml.dump(resultdict, outfile)

        logger.info("Listing directory contents at the end")
        list_directory_contents()
        logger.info(f"Stop condition after module '{stop_after_module}' has been met. Halting workflow execution.")
        sys.exit(0)  # Gracefully exit the script when the condition is met
    else:
        pass
    
    
def validate_stop_after_value(global_calc_settings, logger) -> Union[str, None]:
    """
    Validates that the 'stop_after' key in global_calc_settings is defined and matches a valid Executable.
    If 'stop_after' is not set, the function returns None, allowing the workflow to proceed to the end.

    Parameters:
    - global_calc_settings: The global calculation settings dictionary containing the 'stop_after' key.
    - logger: Logger instance for logging information.

    Returns:
    - The validated stop_after value if it is valid, or None if not set.

    """
    stop_after_value = global_calc_settings.get('stop_after')

    if stop_after_value is None:
        logger.info("'stop_after' is not set in global_calc_settings. The workflow will proceed to the end.")
        return None

    valid_executables = [executable.value for executable in Executable]
    if stop_after_value not in valid_executables:
        logger.error(f"Invalid 'stop_after' value: '{stop_after_value}'. Must be one of: {valid_executables}.")
        sys.exit(f"Exiting due to invalid 'stop_after' value: '{stop_after_value}'.")

    logger.info(f"'stop_after' value is valid: '{stop_after_value}'")
    return stop_after_value
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
# Validate the 'stop_after' setting in global_calc_settings before starting the workflow
stop_module = validate_stop_after_value(global_calc_settings, logger)

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
        sys.exit("Exiting due to mismatched files.")

    if extra_files:
        logger.warning(f"Extra files that have paths specified but are not required by the calculator: {extra_files}. "
                       f"Note: you requested to exit after module {stop_module}. "
                       f"If these files are generated by the modules following {stop_module}, it is okay. "
                       f"But I am not aware of the order in which module are called, "
                       f"that is why I cannot catch possible error in the runtime")

else:
    logger.info("Sanity Check Successful: The Calculator knows paths to the [diadem] files that have to be returned.")

# <--


folder_name = '.'
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

stop_workflow_after_module(stop_module, resultdict, executable, logger)

# 1 -> 2
previous_executable = executable  #

# 2 #########################################
executable = executable.QPPARAMETRIZER_S0_opt
#############################################


try:
    with ChangeDirectory(executable.value):
        # todo: copy the output directory may be a part of the context manager?

        fetch_output_from_previous_executable(previous_executable.value)

        executable_path = find_executable_path(executable.value.split('_')[0])  # QPParametrizer_* -> QPParametrizer
        command = f"{executable_path}"

        source_path = f'{opt_tmpl}/{executable.value}/parametrizer_settings.yml'
        destination_path = pathlib.Path.cwd() / 'parametrizer_settings.yml'  # Current directory
        copy_with_changes(source_path, changes[executable.value], destination_path)

        run_command(command)

        shutil.copy('output_molecule.mol2', 'molecule_S0_opt.mol2')
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

stop_workflow_after_module(stop_module, resultdict, executable, logger)

# 2 -> 3
previous_executable = executable  #

# 3 #########################################
executable = executable.QPPARAMETRIZER_S1_opt
#############################################


try:
    with ChangeDirectory(executable.value):

        fetch_output_from_previous_executable(previous_executable.value)

        executable_path = find_executable_path(executable.value.split('_')[0])  # QPParametrizer_* -> QPParametrizer
        command = f"{executable_path}"

        source_path = f'{opt_tmpl}/{executable.value}/parametrizer_settings.yml'
        destination_path = pathlib.Path.cwd() / 'parametrizer_settings.yml'  # Current directory
        copy_with_changes(source_path, changes[executable.value], destination_path)

        run_command(command)

        shutil.copy('output_molecule.mol2', 'molecule_S1_opt.mol2')
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

stop_workflow_after_module(stop_module, resultdict, executable, logger)


# 2 -> 4
previous_executable = executable.QPPARAMETRIZER_S0_opt  # S0 optimized geometry!

# 4 #############################################
executable = executable.QPPARAMETRIZER_S0_absorbtion
#################################################


try:
    with ChangeDirectory(executable.value):

        fetch_output_from_previous_executable(previous_executable.value)

        executable_path = find_executable_path(executable.value.split('_')[0])  # QPParametrizer_* -> QPParametrizer
        command = f"{executable_path}"

        source_path = f'{opt_tmpl}/{executable.value}/parametrizer_settings.yml'
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

stop_workflow_after_module(stop_module, resultdict, executable, logger)


# 3 -> 5
previous_executable = executable.QPPARAMETRIZER_S1_opt  # S1 optimized geometry!

# 5 ##############################################
executable = executable.QPPARAMETRIZER_S1_emission
##################################################


try:
    with ChangeDirectory(executable.value):

        fetch_output_from_previous_executable(previous_executable.value)

        executable_path = find_executable_path(executable.value.split('_')[0])  # QPParametrizer_* -> QPParametrizer
        command = f"{executable_path}"

        source_path = f'{opt_tmpl}/{executable.value}/parametrizer_settings.yml'
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






# resultdict will be filled in after every workflow step.
# if the workflow succeeds, resultdict is complete.
stop_workflow_after_module(stop_module, resultdict, executable, logger, is_last_module=True)  # if nothing specified, will save results and exit 0
