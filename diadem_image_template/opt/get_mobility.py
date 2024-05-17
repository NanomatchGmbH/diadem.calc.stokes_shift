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
with open("mol.inchi",'w') as outfile:
    outfile.write(f"{inchi}\n")


# 1. get 3D model of the molecule

command = f"obabel -i inchi mol.inchi -o xyz -O mol.xyz --gen3d"
subprocess.check_output(shlex.split(command))

#1.opt. optimizw using xtb from xtb, not from parametrizer.
# we optimize the bad 3d structure
command = "xtb mol.xyz --opt"
output = subprocess.check_output(shlex.split(command), encoding="utf8", text=True).split("\n")

logger.info("Terra incognito")



#1.end: transform to mol2

# Construct the Open Babel command to convert from XYZ to mol2 format
input_xyz = 'xtbopt.xyz'
output_mol2 = 'input_molecule.mol2'
command = f"obabel -i xyz {input_xyz} -o mol2 -O {output_mol2}"
subprocess.check_output(shlex.split(command))

input_molecule = pathlib.Path.cwd() / "input_molecule.mol2"
assert input_molecule.is_file(), f"Required file {input_molecule} does not exist"

env_vars = dict(os.environ)
logger.info("Environment variables at start", environment=env_vars)

# Adding context for some critical environment variables
logger.info("Active Conda environment", conda_env=env_vars.get('CONDA_DEFAULT_ENV', 'N/A'))
logger.info("Number of OpenMP threads", omp_threads=env_vars.get('OMP_NUM_THREADS', 'N/A'))
logger.info("CPU binding policy", slurm_cpu_bind=env_vars.get('SLURM_CPU_BIND', 'N/A'))


# 2. optimize the molecule using Parametrizer, without TM.
# Define the source and destination paths
source_path = '/opt/tmpl/parametrizer/parametrizer_settings.yml'
destination_path = './parametrizer_settings.yml'  # Current directory

# Copy the file
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


#!--> dummy output
for tag in provides:
    resultdict[inchiKey][tag] = 0
#!<--

with open("result.yml",'wt') as outfile:
    yaml.dump(resultdict, outfile)
