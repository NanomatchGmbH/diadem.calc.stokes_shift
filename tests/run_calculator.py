'''
Goal: can be used as a tool to run mobility workflow to to make a stress test / time estimation.
Origin: remake of the test_calculators.py which is run as a regular python script.

'''

import itertools
import pathlib
import shutil
import subprocess
import tempfile
import os
import uuid
import yaml
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def docker_run_helper(image_name: str, workdir: pathlib.Path, molecule: pathlib.Path, calculator: pathlib.Path):
    run_command = [
        "docker", "run", "--rm",
        "-v", "/dev/shm:/dev/shm",
        "-v", f"{workdir}:/tmp",
        "-v", f"{molecule}:/tmp/molecule.yml",
        "-v", f"{calculator}:/tmp/calculator.yml",
        "--workdir", "/tmp", image_name
    ]
    output = subprocess.check_output(run_command, encoding="utf8")
    logging.info(output)


def get_image_name() -> str:
    image_name = subprocess.check_output(["git", "describe"], encoding="utf8").replace('/v', ':')
    return image_name.strip()


def get_molecules(input_dir: pathlib.Path) -> list[pathlib.Path]:
    molpath = input_dir / "molecules"
    files = [*molpath.glob("*.yml")]
    return files


def get_calculators(calculator_dir: pathlib.Path) -> list[pathlib.Path]:
    files = [*calculator_dir.glob("*.yml")]
    return files


def run_calculations(molecule: pathlib.Path, calculator: pathlib.Path, image_name: str,
                     output_dir: pathlib.Path) -> None:
    output_directory = output_dir / calculator.name / molecule.name
    output_directory.mkdir(parents=True, exist_ok=True)

    random_name = uuid.uuid4().hex
    tmpdir = pathlib.Path(f'/tmp/{random_name}')  # workaround
    tmpdir.mkdir()

    os.chmod(tmpdir, 0o777)
    docker_run_helper(image_name, tmpdir, molecule, calculator)

    logfile = tmpdir / "log.txt"
    if logfile.is_file():
        shutil.copy(logfile, output_directory / "log.txt")
    else:
        logging.error("Did not find log.txt")

    optional_files_to_get_back = [
        'molecule_0.spf', 'molecule_0.pdb', 'deposit_init.sh',
        'structure.cml', 'Analysis/files_for_kmc/files_for_kmc.zip'
    ]

    for filename in optional_files_to_get_back:
        file_path = tmpdir / filename
        if file_path.is_file():
            shutil.copy(file_path, output_directory / filename)
        else:
            logging.warning(f"File {filename} not found")

    resultfile = tmpdir / "result.yml"
    if resultfile.is_file():
        ref_resultfile = output_directory / "result_reference.yml"
        if ref_resultfile.is_file():
            with ref_resultfile.open('rt') as infile:
                ref_dict = yaml.safe_load(infile)
            with resultfile.open('rt') as infile:
                result_dict = yaml.safe_load(infile)
            assert ref_dict == result_dict, "Results do not match the reference"
        else:
            logging.info("Did not find reference. Will copy result.yml.")
            shutil.copy(resultfile, ref_resultfile)
    else:
        logging.error("Did not find result.yml")


def main(args):
    image_name = get_image_name()
    molecules = get_molecules(args.input_dir)
    calculators = get_calculators(args.calculator_dir)


    for molecule, calculator in itertools.product(molecules, calculators):
        logging.info(f"Running calculations for molecule: {molecule} with calculator: {calculator}")
        run_calculations(molecule, calculator, image_name, args.output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run mobility workflow using Docker.")
    parser.add_argument('--input-dir', type=pathlib.Path, required=True,
                        help="Directory containing molecule YAML files")
    parser.add_argument('--calculator-dir', type=pathlib.Path, required=True,
                        help="Directory containing calculator YAML files")
    parser.add_argument('--output-dir', type=pathlib.Path, required=True, help="Directory to store output files")

    args = parser.parse_args()
    main(args)
