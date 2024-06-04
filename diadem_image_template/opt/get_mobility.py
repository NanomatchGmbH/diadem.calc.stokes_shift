#!/usr/bin/env python3
import glob
import pathlib
import shutil
import sys
import zipfile

import yaml
import subprocess
import shlex
import structlog
import logging
import os
import uuid
import tempfile
from utils.change_dictionary import copy_with_changes  # todo: rename
from utils.general import load_yaml, save_yaml
import psutil
from contextlib import contextmanager

debug = False
opt_tmpl = "/opt/tmpl"

# Configure structlog
logging.basicConfig(
    filename='log.txt',
    filemode='w',
    format='%(message)s',
    level=logging.INFO
)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Create a logger
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


def run_command(command, use_shell=False, output_file=None):
    """
    Run a shell command and log its output using structlog. Optionally redirect stdout to an output file.
    """
    try:
        logger.info(f"Running command: {command}")
        if use_shell:
            if output_file:
                with open(output_file, 'w') as out_file:
                    result = subprocess.run(command, check=True, stdout=out_file, stderr=subprocess.PIPE, shell=True,
                                            encoding='utf8')
                    logger.info(f"Command stdout written to {output_file}")
                    if result.stderr:
                        logger.error(f"Command stderr: {result.stderr}")
            else:
                result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
                                        encoding='utf8')
                if result.stdout:
                    logger.info(f"Command stdout: {result.stdout}")
                if result.stderr:
                    logger.error(f"Command stderr: {result.stderr}")
        else:
            command_list = shlex.split(command) if isinstance(command, str) else command
            if output_file:
                with open(output_file, 'w') as out_file:
                    result = subprocess.run(command_list, check=True, stdout=out_file, stderr=subprocess.PIPE,
                                            encoding='utf8')
                    logger.info(f"Command stdout written to {output_file}")
                    if result.stderr:
                        logger.error(f"Command stderr: {result.stderr}")
            else:
                result = subprocess.run(command_list, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        encoding='utf8')
                if result.stdout:
                    logger.info(f"Command stdout: {result.stdout}")
                if result.stderr:
                    logger.error(f"Command stderr: {result.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error("Command failed", command=command, returncode=e.returncode, output=e.output, stderr=e.stderr)
        raise
    except FileNotFoundError as e:
        logger.error(f"Command not found: {e.filename}", error=str(e))
        raise


def set_env_variables_from_dict(env_vars):
    '''
    For deposit: helps to set the args
    '''

    def set_env(prefix, d):
        for key, value in d.items():
            if isinstance(value, dict):
                set_env(f"{prefix}.{key}", value)
            else:
                os.environ[f"{prefix}.{key}"] = str(value)

    for key, value in env_vars.items():
        set_env(key, value)

    return dict(os.environ)


# Deposit scripts below -->

def setup_working_directory():
    current_dir = os.getcwd()
    scratch_dir = os.environ.get('SCRATCH')
    home_dir = os.environ.get('HOME')
    generated_uuid = os.environ.get('GENERATED_UUID', 'default_uuid')  # Set a default UUID if not provided

    if scratch_dir and os.path.isdir(scratch_dir):
        working_dir = os.path.join(scratch_dir, os.getlogin(), generated_uuid)
    elif home_dir and os.path.isdir(home_dir):
        working_dir = os.path.join(home_dir, 'tmp', generated_uuid)
    else:
        working_dir = current_dir

    os.makedirs(working_dir, exist_ok=True)
    for item in os.listdir(current_dir):
        s = os.path.join(current_dir, item)
        d = os.path.join(working_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

    logger.info(f"Deposit running on node {os.uname().nodename} in directory {working_dir}")
    os.chdir(working_dir)
    return current_dir, working_dir


def check_and_extract_deposit_restart():
    if os.environ.get('DO_RESTART') == 'True':
        if os.path.isfile('restartfile.zip'):
            with zipfile.ZipFile('restartfile.zip', 'r') as zip_ref:
                zip_ref.testzip()
                if zip_ref.testzip() is not None:
                    print("Could not read restartfile. Aborting run.")
                    exit(1)
                print("Found Checkpoint, extracting for restart.")
                zip_ref.extractall()
            os.remove('restartfile.zip')
        else:
            print("Restart was enabled, but no checkpoint file was found. Not starting simulation.")
            exit(5)


def convert_structure():
    run_command("obabel structure.cml -O structure.mol2", use_shell=True)


def deposit_simulation():
    command = (
        "Deposit molecule.0.pdb=molecule_0.pdb molecule.0.spf=molecule_0.spf molecule.0.conc=1.0 "
        "simparams.Thi=4000.0 simparams.Tlo=300.0 simparams.sa.Tacc=5.0 simparams.sa.cycles=${UC_PROCESSORS_PER_NODE} "
        "simparams.sa.steps=${simparams.sa.steps} simparams.Nmol=${simparams.Nmol} simparams.moves.dihedralmoves=True "
        "Box.Lx=${Box.Lx} Box.Ly=${Box.Ly} Box.Lz=${Box.Lz} Box.pbc_cutoff=10.0 simparams.PBC=${simparams.PBC} "
        "machineparams.ncpu=${UC_PROCESSORS_PER_NODE} Box.grid_overhang=${Box.grid_overhang} "
        "simparams.postrelaxation_steps=${simparams.postrelaxation_steps}"
    )
    expanded_command = os.path.expandvars(command)
    run_command(expanded_command, use_shell=True)


def add_periodic_copies_deposit():
    if True:
        run_command("$DEPTOOLS/add_periodic_copies.py 7.0", use_shell=True)
        shutil.move("periodic_output/structurePBC.cml", ".")
        shutil.rmtree("periodic_output/", ignore_errors=True)


def create_deposit_restart_zip():
    with zipfile.ZipFile('restartfile.zip', 'w') as zipf:
        for file in ["deposited_*.pdb.gz", "static_parameters.dpcf.gz",
                     "static_parameters.dpcf_molinfo.dat.gz", "grid.vdw.gz",
                     "grid.es.gz", "neighbourgrid.vdw.gz"]:
            for matched_file in glob.glob(file):
                zipf.write(matched_file)
                os.remove(matched_file)


def handle_deposit_working_dir_cleanup(current_dir, working_dir):
    data_dir = current_dir

    logger.info(f"Cleaning up working directory: {working_dir}")

    if working_dir != data_dir:
        os.makedirs(data_dir, exist_ok=True)
        for item in os.listdir(working_dir):
            s = os.path.join(working_dir, item)
            d = os.path.join(data_dir, item)
            try:
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    if s != d:  # Ensure source and destination are not the same
                        shutil.copy2(s, d)
            except Exception as e:
                logger.warning(f"Failed to copy {s} to {d}: {e}")

        for root, dirs, files in os.walk(data_dir):
            for file in files:
                if file in ["*.stderr", "*.stdout", "stdout", "stderr"]:
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception as e:
                        logger.warning(f"Failed to remove {os.path.join(root, file)}: {e}")

        try:
            shutil.rmtree(working_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to remove working directory {working_dir}: {e}")


def list_installed_micromamba_packages():
    try:
        result = subprocess.run(['micromamba', 'list'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                encoding='utf8')
        installed_packages = result.stdout
        logger.info("Installed packages:\n" + installed_packages)
    except subprocess.CalledProcessError as e:
        logger.error("Failed to list installed packages", error=str(e))
        raise


def run_analysis():
    #    run_command("QuantumPatchAnalysis", use_shell=True)
    #    run_command("QuantumPatchAnalysis Analysis.Density.enabled=True Analysis.RDF.enabled=True", use_shell=True)
    pass


def append_settings():
    with open("deposit_settings.yml", "r") as settings_file:
        settings_data = settings_file.read()
    with open("output_dict.yml", "a") as output_file:
        output_file.write(settings_data)


# <-- Deposit scripts below


def run_shell_script(script_path, env_vars):
    """
    Run a shell script and log its output using structlog.
    """
    try:
        logger.info(f"Running shell script: {script_path}")
        result = subprocess.run(
            f'bash {script_path}',
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env_vars
        )
        logger.info(f"Script output:\n{result.stdout}")
        if result.stderr:
            logger.error(f"Script error output:\n{result.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Script failed with return code {e.returncode}", error=str(e))
        raise


def check_required_output_files_exist(filepaths, description="file"):
    """
    Check if a file or list of files exist in the current working directory and log a critical error if any do not.
    Raise FileNotFoundError if any file is missing.
    """
    if isinstance(filepaths, (str, pathlib.Path)):
        filepaths = [filepaths]

    cwd = pathlib.Path.cwd()
    missing_files = [str(filepath) for filepath in filepaths if not (cwd / filepath).is_file()]

    if missing_files:
        logger.critical(f"Required {description}(s) missing in current working directory: {', '.join(missing_files)}")
        raise FileNotFoundError(
            f"Required {description}(s) missing in current working directory: {', '.join(missing_files)}")


@contextmanager
def change_directory(destination):  # todo remove
    """
    Context manager for changing the current working directory.
    """
    original_dir = pathlib.Path.cwd()
    try:
        os.chdir(destination)
        yield
    finally:
        os.chdir(original_dir)


class ChangeDirectory:
    """
    Context manager for creating and changing the current working directory to a simulations directory.
    """

    def __init__(self, dir_name):
        self.new_path = pathlib.Path.cwd() / dir_name
        self.original_path = pathlib.Path.cwd()

    def __enter__(self):
        self.new_path.mkdir(exist_ok=True)
        os.chdir(self.new_path)
        logger.info(f"Changed directory to {self.new_path}")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.original_path)
        logger.info(f"Returned to original directory {self.original_path}")


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
    'global')  # contains things which are general to all specifications, in this case to all tools. Line number of cpus.

#we read smiles and molid
inchi = moldict["inchi"]
inchiKey = moldict["inchiKey"]



# 1 .PREOPTIMIZATION WITH NO NM SOFTWARE
# Create a new directory for preoptimization
# we generate a bad 3d structure. Plan below:
# mol.inchi -[obabel]-> mol.xyz ->[xtb]-> xtbout.xyz -[obabel]-> input_molecule.mol2

with ChangeDirectory("preoptimization"):
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
    command = f"xtb {initial_conformer_xyz} --opt"  # outputs xtbout.xyz
    run_command(command)
    xtb_preoptimized_xyz = 'xtbopt.xyz'
    required_files = [xtb_preoptimized_xyz]
    check_required_output_files_exist(required_files)

    logger.info("Transfer xyz to mol2 . . .")
    xtb_preoprimized_mol2 = 'input_molecule.mol2'
    command = f"obabel -i xyz {xtb_preoptimized_xyz} -o mol2 -O {xtb_preoprimized_mol2}"
    run_command(command)
    required_files = [xtb_preoprimized_mol2]
    check_required_output_files_exist(required_files)

logger.info(". . . Preoptimization successful!")

# 2. Parametrizer.


executable = "QPParametrizer"  # name of the [main] entrypoint that will be run.
command = f"{executable}"
source_path = f'{opt_tmpl}/QPParametrizer/parametrizer_settings.yml'
destination_path = './parametrizer_settings.yml'  # Current directory
copy_with_changes(source_path, changes[executable], destination_path)  # executable == calculator['configuration']!

run_command(command)

# ensure the output exists
output_molecule_mol2_from_parametrizer = "output_molecule.mol2"
molecule_spf_from_parametrizer = "molecule.spf"
required_files = [output_molecule_mol2_from_parametrizer, molecule_spf_from_parametrizer]

for required_file in required_files:
    assert (pathlib.Path.cwd() / required_file).is_file(), f"Required file {required_file} does not exist"
if debug:
    list_directory_contents()
sys.exit()



# 3. DHP.
logger.info("DHP starts . . .")

# 3.0. Prepare DHP or anything using HOSTFILE
# todo: make a function write hostile.

#numcpus = psutil.cpu_count()

numcpus = 30  # todo remove

# todo Timo hostfile is configued in  q
hostfile_path = os.environ.get('HOSTFILE', 'generated_hostfile.txt')  # it might be set from above.  # todo remove?
os.environ['HOSTFILE'] = hostfile_path
# Open the HOSTFILE for appending
with open(hostfile_path, 'a') as hostfile:
    for i in range(numcpus):
        hostfile.write("localhost\n")
# todo: end of todo

# Run add_dihedral_angles.sh

# Ensure DEPTOOLS is set in the environment
dep_tools = os.environ.get('DEPTOOLS')
if not dep_tools:
    logger.error("DEPTOOLS environment variable is not set")
    raise EnvironmentError("DEPTOOLS environment variable is not set")

# Add dihedral angles
command = f"{dep_tools}/add_dihedral_angles.sh {output_molecule_mol2_from_parametrizer} {molecule_spf_from_parametrizer}"
run_command(command)

# Zip files
command = f"zip report.zip {output_molecule_mol2_from_parametrizer} molecule.pdb {molecule_spf_from_parametrizer}"
run_command(command)

# Append mol_data.yml to output_dict.yml ### artem: why do we need this at all?
#command = "cat mol_data.yml >> output_dict.yml"

# Convert mol2 to svg
command = "obabel -imol2 output_molecule.mol2 -osvg"
run_command(command, output_file="output_molecule.svg")

source_path = f'{opt_tmpl}/DihedralParametrizer/dhp_settings.yml'
destination_path = './dhp_settings.yml'  # Current directory

copy_with_changes(source_path, changes["DihedralParametrizer"], destination_path)

if debug:  # check if the template was changed according to the calculator
    source_dict, destination_dict = load_yaml(source_path), load_yaml(destination_path)
    logger.info("DHP settings template and actually used", extra={'before': source_dict, 'after': destination_dict})

# list_directory_contents()

# ensure that the necessary files exist and their files are as expected
output_molecule_pdb_after_add_dyhedrals = "molecule.pdb"
output_molecule_spf_after_add_dyhedrals = "molecule.spf"
dhp_settings = "dhp_settings.yml"

required_files = [output_molecule_pdb_after_add_dyhedrals, output_molecule_spf_after_add_dyhedrals,
                  dhp_settings]
for required_file in required_files:
    assert (pathlib.Path.cwd() / required_file).is_file(), f"Required file {required_file} does not exist"

# which is DHP?
try:
    result = subprocess.run(['which', 'DihedralParametrizer'], check=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, encoding='utf8')
    dihedral_parametrizer_path = result.stdout.strip()
    logger.info(f"Found DihedralParametrizer at {dihedral_parametrizer_path}")
except subprocess.CalledProcessError as e:
    logger.error("Failed to find DihedralParametrizer", error=str(e))
    raise

# Run DihedralParametrizer with MPI
command = f"mpirun --bind-to none $NMMPIARGS $ENVCOMMAND --hostfile $HOSTFILE --mca btl self,vader,tcp python -m mpi4py {dihedral_parametrizer_path} ./dhp_settings.yml"
run_command(command, use_shell=True)

# Create symbolic links
#os.symlink('molecule.pdb', 'molecule_0.pdb')
#os.symlink('dihedral_forcefield.spf', 'molecule_0.spf')

shutil.copy('molecule.pdb', 'molecule_0.pdb')  # deposit_init change?
shutil.copy('dihedral_forcefield.spf', 'molecule_0.spf')  # deposit_init change?

# list_directory_contents()

# 4. Deposit.
logger.info("Deposit starts . . .")

# 4.0. Copy deposit_init.sh to the current dir.

source_path = f'{opt_tmpl}/Deposit/deposit_init.sh'
destination_path = './deposit_init.sh'  # Current directory

# Copy deposit_init.sh.
try:
    shutil.copy(source_path, destination_path)
    print(f"Copied {source_path} to {destination_path}")
except Exception as e:
    logger.error("Failed to copy the file", error=str(e))
    raise

# copy_with_changes(
#     source_path, changes['Deposit'], destination_path
# )


set_env_variables_from_dict(changes['Deposit'])

# Generate a UUID in Python
generated_uuid = str(uuid.uuid4())
logger.info(f"Generated UUID: {generated_uuid}")

# Set necessary environment variables
env_vars = os.environ.copy()
env_vars['GENERATED_UUID'] = generated_uuid

script_path = 'deposit_init.sh'  # the way deposit is run is different
run_shell_script(script_path, env_vars)

# deposit_init commands -->
# current_dir, working_dir = setup_working_directory()
# check_and_extract_deposit_restart()
# deposit_simulation()
# convert_structure()
# add_periodic_copies_deposit()
# create_deposit_restart_zip()
# handle_deposit_working_dir_cleanup(current_dir, working_dir)
# # run_analysis()
# # append_settings()
#
# os.chdir(current_dir)
# <-- deposit_init commands

if debug:
    list_directory_contents()
# todo check output files.

# 5. QP.
logger.info("QP starts . . .")

# 5.0. Copy deposit_init.sh to the current dir.

source_path = f'{opt_tmpl}/QuantumPatch/settings_ng.yml'
destination_path = './settings_ng.yml'  # Current directory

# Copy settings_ng.yml of QP

copy_with_changes(source_path, changes['QuantumPatch'], destination_path)

# Generate a random directory inside the current directory
current_dir = os.getcwd()
scratch_dir = os.path.join(current_dir, "qp_scratch_" + next(tempfile._get_candidate_names()))

# Ensure the directory exists
os.makedirs(scratch_dir, exist_ok=True)

# Set the SCRATCH environment variable
os.environ['SCRATCH'] = scratch_dir

# Print the SCRATCH directory to verify
logger.info(f"SCRATCH for QuantumPatch is set to: {os.environ['SCRATCH']}")

# 5.1. RUN QP

# the only necessary input for QP: structure or structurePBC is in the current folder.

# which is QP?
try:
    result = subprocess.run(['which', 'QuantumPatch'], check=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, encoding='utf8')
    qp_path = result.stdout.strip()
    logger.info(f"Found QuantumPatch at {qp_path}")
except subprocess.CalledProcessError as e:
    logger.error("Failed to find QuantumPatch", error=str(e))
    raise

os.environ['OMP_NUM_THREADS'] = '1'

# command = f'mpirun --bind-to none -np 30 $NMMPIARGS $ENVCOMMAND --hostfile $HOSTFILE --mca btl self,vader,tcp python -m mpi4py {qp_path}'
command = f'mpirun --bind-to none -np 30 $NMMPIARGS $ENVCOMMAND --mca btl self,vader,tcp python -m mpi4py {qp_path}'  # todo not hard code
run_command(command, use_shell=True)  # use or not use?

# todo check if output files are there.

# 5.2. Prepare input for LF

# Define the directory to be zipped and the name of the zip file: needed for lightforge
directory_to_zip = "Analysis"
zip_file_name = "QP_output_0.zip"

# Create a zip from Analysis of QP.
with zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Walk through the directory
    for root, dirs, files in os.walk(directory_to_zip):
        for file in files:
            # Create the complete filepath of the file in the zip
            file_path = os.path.join(root, file)
            # Add the file to the zip file, preserving the directory structure
            zipf.write(file_path, os.path.relpath(file_path, directory_to_zip))

logger.info(f"Directory '{directory_to_zip}' zipped into '{zip_file_name}' successfully. This will be the LF input.")

# 5. Lightforge

source_path = f'{opt_tmpl}/lightforge/settings'
destination_path = './settings'

# Copy settings of LF to the current dir
# try:
#     shutil.copy(source_path, destination_path)
#     print(f"Copied {source_path} to {destination_path}")
# except Exception as e:
#     logger.error("Failed to copy the file", error=str(e))
#     raise

copy_with_changes(source_path, changes['lightforge'], destination_path)

try:
    result = subprocess.run(['which', 'lightforge'], check=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, encoding='utf8')
    lightforge_path = result.stdout.strip()
    logger.info(f"Found lightforge at {lightforge_path}")
except subprocess.CalledProcessError as e:
    logger.error("Failed to find lightforge", error=str(e))
    raise

os.environ['OMP_NUM_THREADS'] = '1'
command = f'mpirun -x OMP_NUM_THREADS --bind-to none -n {numcpus} --mca btl self,vader,tcp python -m mpi4py {lightforge_path} -s settings'
run_command(command, use_shell=True)

# todo check.


# Finalizing -->
resultdict = {inchiKey: {}}  # dummy output

# before we extract and write the results, we want to show what we have in the working dir after simulations are complete

logger.info("Listing directory contents at the end")
list_directory_contents()

#!--> dummy output
for tag in provides:
    resultdict[inchiKey][tag] = 0
#!<--

with open("result.yml", 'wt') as outfile:
    yaml.dump(resultdict, outfile)
