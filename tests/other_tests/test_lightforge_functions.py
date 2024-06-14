import pytest
import yaml
import tempfile
import pathlib
from diadem_image_template.opt.utils.lightforge_functions import set_carrier_type

# Sample YAML content to be used for tests
sample_yaml_content = """
pbc: [True, True, True]
expansion_scheme: edcm

particles:
 holes: True
 electrons: False
 excitons: False

morphology_width: 40

QP_output_files:
- name: molA
  QP_output.zip: QP_output_0.zip

materials:
- name: htl
  input_mode_transport: "QP: sig PAR: eaip,l"
  molecule_parameters:
    molecule_pdb: molecule_0.pdb
    QP_output_sigma: molA
    energies:
    - [5.0, 2.0]
    - [0.2, 0.2]

layers:
- thickness: 40
  morphology_input_mode: automatic
  molecule_species:
  - material: htl
    concentration: 1.0

neighbours: 120
transfer_integral_source: QP_output
superexchange: True

pair_input:
 - molecule 1: htl
   molecule 2: htl
   QP_output:  molA

experiments:
- simulations: 10
  measurement: DC
  Temperature: 300
  field_direction: [1, 0, 0]
  field_strength: 0.02 0.03 0.04
  initial_holes: 30

iv_fluctuation: 0.001
new_wano: True
max_iterations: 10000000
ti_prune: True

live_reporting:
  reporting_time_interval: 15
  IV: False
  density: False
"""


@pytest.fixture
def create_temp_yaml():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".yml") as tmp:
        tmp.write(sample_yaml_content.encode())
        tmp_path = tmp.name
    yield tmp_path
    pathlib.Path(tmp_path).unlink()  # Clean up the temporary file


def test_set_carrier_type_hole(create_temp_yaml):
    set_carrier_type(create_temp_yaml, 'hole')
    with open(create_temp_yaml, 'r') as file:
        config = yaml.safe_load(file)

    assert config['particles']['holes'] is True
    assert config['particles']['electrons'] is False
    assert 'initial_holes' in config['experiments'][0]
    assert 'initial_electrons' not in config['experiments'][0]


def test_set_carrier_type_electron(create_temp_yaml):
    set_carrier_type(create_temp_yaml, 'electron')
    with open(create_temp_yaml, 'r') as file:
        config = yaml.safe_load(file)

    assert config['particles']['holes'] is False
    assert config['particles']['electrons'] is True
    assert 'initial_electrons' in config['experiments'][0]
    assert 'initial_holes' not in config['experiments'][0]


def test_set_carrier_type_invalid():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".yml") as tmp:
        tmp.write(sample_yaml_content.encode())
        tmp_path = tmp.name

    with pytest.raises(ValueError, match="carrier_type must be either 'hole' or 'electron'"):
        set_carrier_type(tmp_path, 'invalid')

    pathlib.Path(tmp_path).unlink()  # Clean up the temporary file
