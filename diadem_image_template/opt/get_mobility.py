#!/usr/bin/env python3
import pathlib
import shutil

import yaml
import subprocess
import shlex
import structlog
import logging
import os

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
            logger.info(f"Found item: {item.name}", item_type="directory" if item.is_dir() else "file", size=item.stat().st_size)
        return contents
    except Exception as e:
        logger.error("Failed to list directory contents", error=str(e))
        raise


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


# 2. Parametrizer.
# Define the source and destination paths
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

###### -->
# we calculate homo and lumo
#command = "xtb xtbopt.xyz"
#output = subprocess.check_output(shlex.split(command), encoding="utf8", text=True).split("\n")

#with open("out.log",'wt') as outfile:
#    outfile.write("\n".join(output))
###### <--

resultdict =  { inchiKey: {} }  # dummy output

###### -->
#for line in output:
#    for tag in provides:
#        if f"({tag})" in line: # xtb logs homo lumo out as (HOMO) and (LUMO)
#            splitline = line.split()
#            value = float(splitline[-2])
#            resultdict[inchiKey][tag] = value
###### <--

# before we extract and write the results, we want to show what we have in the working dir after simulations are complete

logger.info("Listing directory contents at the end")
list_directory_contents()


#!--> dummy output
for tag in provides:
    resultdict[inchiKey][tag] = 0
#!<--

with open("result.yml",'wt') as outfile:
    yaml.dump(resultdict, outfile)
