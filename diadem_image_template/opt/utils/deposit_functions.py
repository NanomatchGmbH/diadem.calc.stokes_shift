from .logging_config import configure_logging
import structlog
import os
import shutil
import zipfile
import glob
from .subprocess_functions import run_command

# Ensure the logging configuration is applied
configure_logging()

# Get the logger
logger = structlog.get_logger()


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
    # todo: here, because unable using rsync, data were first copied to the data dir and then removed from data_dir. Nonsense!
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

        # Remove specific log files
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                if file.endswith((".stderr", ".stdout")) or file in ["stdout", "stderr"]:
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception as e:
                        logger.warning(f"Failed to remove {os.path.join(root, file)}: {e}")

        # Change to data directory
        try:
            os.chdir(data_dir)
            logger.info(f"Changed directory to {data_dir}")
        except Exception as e:
            logger.warning(f"Failed to change directory to {data_dir}: {e}")

        # Remove the working directory
        try:
            shutil.rmtree(working_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to remove working directory {working_dir}: {e}")


def run_analysis():
    run_command(
        "QuantumPatchAnalysis",
        use_shell=True,
        output_file='DensityAnalysisInit.out'
    )
    run_command(
        "QuantumPatchAnalysis Analysis.Density.enabled=True Analysis.RDF.enabled=True",
        use_shell=True,
        output_file='DensityAnalysis.out'
    )


def append_settings():
    with open("deposit_settings.yml", "r") as settings_file:
        settings_data = settings_file.read()
    with open("output_dict.yml", "a") as output_file:
        output_file.write(settings_data)
