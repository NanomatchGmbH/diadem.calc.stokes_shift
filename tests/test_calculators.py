import itertools
import pathlib
import shutil
import subprocess
import tempfile
import os
import uuid

import pytest
import yaml


def docker_run_helper(image_name: str, workdir: pathlib.Path, molecule: pathlib.Path, calculator: pathlib.Path):
    run_command = ["docker","run","--rm", "-v", "/dev/shm:/dev/shm", "-v", f"{workdir}:/tmp", "-v",  f"{molecule}:/tmp/molecule.yml","-v", f"{calculator}:/tmp/calculator.yml","--workdir","/tmp", image_name]
    output = subprocess.check_output(run_command,encoding="utf8")

@pytest.fixture
def image_name():
    image_name = subprocess.check_output(["git","describe"], encoding="utf8").replace('/v',':')
    return image_name.strip()

def molecules() -> list[pathlib.Path]:
    molpath = pathlib.Path(__file__).parent / "inputs" / "molecules"
    files = [*molpath.glob("*.yml")]
    return files


def calculators() -> list[pathlib.Path]:
    calcpath = pathlib.Path(__file__).parent / ".." / "calculators"
    files = [*calcpath.glob("*.yml")]
    return files


#def handle_remove_readonly(func, path, exc):
    # Adjust the permissions and reattempt the operation
#    exc_type, exc_value, exc_tb = exc
#    os.chmod(path, 0o777)
#    func(path)

optional_files_to_get_back = ['molecule_0.spf', 'molecule_0.pdb', 'deposit_init.sh', 'structure.cml']


@pytest.mark.parametrize("molecule, calculator", itertools.product(molecules(), calculators()))
def test_calculators(molecule: pathlib.Path, calculator: pathlib.Path, image_name: str) -> None:
    output_directory = pathlib.Path(__file__).parent / "test_outputs" / calculator.name / molecule.name
    output_directory.mkdir(parents=True, exist_ok=True)
    # with tempfile.TemporaryDirectory() as tmpdir:

    random_name = uuid.uuid4().hex
    tmpdir = f'/tmp/{random_name}'  # workaround
    os.mkdir(tmpdir)

    os.chmod(tmpdir, 0o777)
    docker_run_helper(image_name, tmpdir, molecule, calculator)

    logfile = pathlib.Path(tmpdir) / "log.txt"
    assert logfile.is_file(), "Did not find log.txt"
    shutil.copy(logfile, output_directory / "log.txt")

    if optional_files_to_get_back:
        print("Trying to copy additional files . . .")
        for filename in optional_files_to_get_back:
            file_path = pathlib.Path(tmpdir) / filename
            try:
                shutil.copy(file_path, output_directory / filename)
                print("Trying to copy additional files . . .")
            except FileNotFoundError:
                print(f"File {filename} not found")

    resultfile = pathlib.Path(tmpdir)/"result.yml"
    assert resultfile.is_file(), "Did not find result.yml"
    ref_resultfile = output_directory/"result_reference.yml"
    if ref_resultfile.is_file():
        with ref_resultfile.open('rt') as infile:
            ref_dict = yaml.safe_load(infile)
        with resultfile.open('rt') as infile:
            result_dict = yaml.safe_load(infile)
        assert ref_dict == result_dict
    else:
        print("Did not find reference. Will copy result.yml.")
        shutil.copy(resultfile, ref_resultfile)
        #shutil.rmtree(tmpdir, onerror=handle_remove_readonly)
