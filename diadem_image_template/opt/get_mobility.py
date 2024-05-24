#!/usr/bin/env python3
import pathlib
import shutil

import yaml
import subprocess
import shlex
import structlog
import logging
import os
import uuid
import tempfile

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


def check_ssh_installed():
    """
    Check if ssh is installed and available in the system's PATH.
    """
    try:
        result = subprocess.run(['which', 'ssh'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            logger.info("ssh is installed and available in PATH.")
            return True
        else:
            logger.error("ssh is not available in PATH.")
            return False
    except subprocess.CalledProcessError:
        logger.error("ssh is not installed or not available in PATH.")
        return False


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

# List all installed executables in the environment
try:
    result = subprocess.run(['micromamba', 'list'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            encoding='utf8')
    installed_packages = result.stdout
    logger.info("Installed packages:\n" + installed_packages)
except subprocess.CalledProcessError as e:
    logger.error("Failed to list installed packages", error=str(e))
    raise

# remove this -->
# Ensure ssh is available
if not check_ssh_installed():
    logger.error("Please install ssh and ensure it is available in the system's PATH.")
    raise SystemExit("ssh is not available. Exiting.")
# <-- remove this


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

# The engine, which was instantiated needs to provide "provides" (e.g HOMO and LUMO)
provides = calcdict["provides"]

# This is a free form dictionary. For the example, we just provide numsteps
#### steps = calcdict["specification"]["numsteps"]

#we read smiles and molid
inchi = moldict["inchi"]
inchiKey = moldict["inchiKey"]

# we generate a bad 3d structure
mol_inchi = 'mol.inchi'
with open(mol_inchi, 'w') as outfile:
    outfile.write(f"{inchi}\n")

# 1. get 3D model of the molecule

logger.info("Generate 3D conformer of the molecule . . .")

initial_conformer_xyz = 'mol.xyz'
command = f"obabel -i inchi {mol_inchi} -o xyz -O {initial_conformer_xyz} --gen3d"
subprocess.check_output(shlex.split(command))

#1.opt. optimizw using xtb from xtb, not from parametrizer.
# we optimize the bad 3d structure
command = "xtb mol.xyz --opt"
output = subprocess.check_output(shlex.split(command), encoding="utf8", text=True).split("\n")

logger.info("Transfer xyz to mol2 . . .")

#1.end: transform to mol2

# Construct the Open Babel command to convert from XYZ to mol2 format
input_xyz = 'xtbopt.xyz'
output_mol2 = 'input_molecule.mol2'
command = f"obabel -i xyz {input_xyz} -o mol2 -O {output_mol2}"
subprocess.check_output(shlex.split(command))

input_molecule_for_parametrizer = pathlib.Path.cwd() / output_mol2
assert input_molecule_for_parametrizer.is_file(), f"Required file {input_molecule_for_parametrizer} does not exist"

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

# 2. Parametrizer.
# fetch parametrizer settings into the currrent directory
source_path = '/opt/tmpl/parametrizer/parametrizer_settings.yml'
destination_path = './parametrizer_settings.yml'  # Current directory

# Copy the parametrizer_settings.yml 
try:
    shutil.copy(source_path, destination_path)
    print(f"Copied {source_path} to {destination_path}")
except Exception as e:
    logger.error("Failed to copy the file", error=str(e))
    raise

# Define the command
command = "QPParametrizer"

try:
    process = subprocess.Popen(
        shlex.split(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf8",
        text=True,
        env=os.environ
    )
    stdout, stderr = process.communicate()

    # Log stdout and stderr
    logger.info("Command stdout", output=stdout)
    logger.error("Command stderr", error=stderr)

    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command, output=stdout, stderr=stderr)

    print("Command output:", stdout)
except subprocess.CalledProcessError as e:
    logger.error("Failed to run QPParametrizer", error=str(e), output=e.output, stderr=e.stderr)
    raise
except Exception as e:
    logger.error("An error occurred", error=str(e))
    raise

# check after Parametrizer:
output_molecule_mol2_from_parametrizer = "output_molecule.mol2"
molecule_spf_from_parametrizer = "molecule.spf"
required_files_after_parametrizer = [output_molecule_mol2_from_parametrizer, molecule_spf_from_parametrizer]
for required_file in required_files_after_parametrizer:
    assert (pathlib.Path.cwd() / required_file).is_file(), f"Required file {required_file} does not exist"

# 3. DHP.
logger.info("DHP starts . . .")

# 3.0. Prepare DHP or anything using HOSTFILE
numcpus = int(os.environ.get('NUMCPUS', os.cpu_count()))
hostfile_path = os.environ.get('HOSTFILE', 'generated_hostfile.txt')  # it might be set from above.
os.environ['HOSTFILE'] = hostfile_path

# Open the HOSTFILE for appending
with open(hostfile_path, 'a') as hostfile:
    for i in range(numcpus):
        hostfile.write("localhost\n")

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
#run_command(command)

# Convert mol2 to svg
# Convert mol2 to svg
command = "obabel -imol2 output_molecule.mol2 -osvg"
run_command(command, output_file="output_molecule.svg")

source_path = '/opt/tmpl/dhp/dhp_settings.yml'
destination_path = './dhp_settings.yml'  # Current directory

# Copy the parametrizer_settings.yml
try:
    shutil.copy(source_path, destination_path)
    print(f"Copied {source_path} to {destination_path}")
except Exception as e:
    logger.error("Failed to copy the file", error=str(e))
    raise

# check before we run DHP, if we have necessary files.from
# todo: ensure expected files exist

logger.info("Listing directory contents before we run DHP")
list_directory_contents()

# ensure that the necessary files exist and their files are as expected
output_molecule_pdb_after_add_dyhedrals = "molecule.pdb"
output_molecule_spf_after_add_dyhedrals = "molecule.spf"
dhp_settings = "dhp_settings.yml"

required_files_after_parametrizer = [output_molecule_pdb_after_add_dyhedrals, output_molecule_spf_after_add_dyhedrals,
                                     dhp_settings]
for required_file in required_files_after_parametrizer:
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
#command = "mpirun --bind-to none $NMMPIARGS $ENVCOMMAND --hostfile $HOSTFILE --mca btl self,vader,tcp python -m mpi4py `which DihedralParametrizer` dhp_settings.yml >> DHP_mainout.txt 2> dhp_mpi_stderr"
#command = "mpirun --bind-to none $NMMPIARGS $ENVCOMMAND --hostfile $HOSTFILE --mca btl self,vader,tcp python -m mpi4py `which DihedralParametrizer` dhp_settings.yml"
command = f"mpirun --bind-to none $NMMPIARGS $ENVCOMMAND --hostfile $HOSTFILE --mca btl self,vader,tcp python -m mpi4py {dihedral_parametrizer_path} ./dhp_settings.yml"
# command = (f"mpirun --bind-to none --mca plm isolated {os.environ.get('NMMPIARGS')} {os.environ.get('ENVCOMMAND')} "
#                f"--hostfile {os.environ.get('HOSTFILE')} --mca btl self,vader,tcp python -m mpi4py `which DihedralParametrizer` dhp_settings.yml")
run_command(command, use_shell=True)

# Create symbolic links
#os.symlink('molecule.pdb', 'molecule_0.pdb')
#os.symlink('dihedral_forcefield.spf', 'molecule_0.spf')

shutil.copy('molecule.pdb', 'molecule_0.pdb')
shutil.copy('dihedral_forcefield.spf', 'molecule_0.spf')

# 4. Deposit.
logger.info("Deposit starts . . .")

# 4.0. Copy deposit_init.sh to the current dir.

source_path = '/opt/tmpl/deposit/deposit_init.sh'  # todo: 2 molecules if testing . . .
destination_path = './deposit_init.sh'  # Current directory

# Copy deposit_init.sh
try:
    shutil.copy(source_path, destination_path)
    print(f"Copied {source_path} to {destination_path}")
except Exception as e:
    logger.error("Failed to copy the file", error=str(e))
    raise


# Generate a UUID in Python
generated_uuid = str(uuid.uuid4())
logger.info(f"Generated UUID: {generated_uuid}")

# Set necessary environment variables
env_vars = os.environ.copy()
env_vars['GENERATED_UUID'] = generated_uuid

script_path = 'deposit_init.sh'  # the way deposit is run is different
run_shell_script(script_path, env_vars)

# 5. QP.
logger.info("QP starts . . .")

# 4.0. Copy deposit_init.sh to the current dir.

source_path = '/opt/tmpl/qp/settings_ng.yml'  # todo: 2 molecules if testing . . .
destination_path = './settings_ng.yml'  # Current directory

# Copy settings_ng.yml of QP
try:
    shutil.copy(source_path, destination_path)
    print(f"Copied {source_path} to {destination_path}")
except Exception as e:
    logger.error("Failed to copy the file", error=str(e))
    raise


# Generate a random directory inside the current directory
current_dir = os.getcwd()
scratch_dir = os.path.join(current_dir, "scratch_" + next(tempfile._get_candidate_names()))

# Ensure the directory exists
os.makedirs(scratch_dir, exist_ok=True)

# Set the SCRATCH environment variable
os.environ['SCRATCH'] = scratch_dir

# Print the SCRATCH directory to verify
print(f"SCRATCH is set to: {os.environ['SCRATCH']}")

# 4.1. RUN QP
# which is QP?
try:
    result = subprocess.run(['which', 'QuantumPatch'], check=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, encoding='utf8')
    qp_path = result.stdout.strip()
    logger.info(f"Found DihedralParametrizer at {qp_path}")
except subprocess.CalledProcessError as e:
    logger.error("Failed to find DihedralParametrizer", error=str(e))
    raise


command = f'mpirun --bind-to none $NMMPIARGS $ENVCOMMAND --hostfile $HOSTFILE --mca btl self,vader,tcp python -m mpi4py {qp_path}'
run_command(command, use_shell=True)  # use or not use?


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
