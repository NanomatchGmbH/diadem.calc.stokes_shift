import pytest
import yaml
import tempfile
import os
from diadem_image_template.opt.utils.result import get_result_from


def test_QPAnalyzeStokesShift():
    # Define initial local_result dictionary
    local_result = {
        'stokes_shift': {
            'value': None,
            'results': {
                'Stokes shift in eV': {'value': None},
                'Stokes shift in nm': {'value': None},
                'E(S1,S0_opt) in eV': {'value': None},
                'E(S1,S0_opt) in nm': {'value': None},
                'E(S1,S1_opt) in eV': {'value': None},
                'E(S1,S1_opt) in nm': {'value': None},
            }
        }
    }

    # Define results_yml content
    results_yml_content = {
        'Stokes shift results:': {
            'Excitation energy S0-S1 (S0 opt geometry) in eV:': 5.550755161410007,
            'Excitation energy S0-S1 (S0 opt geometry) in nm:': 223.39302742458096,
            'Excitation energy S0-S1 (S1 opt geometry) in eV:': 5.585605414698123,
            'Excitation energy S0-S1 (S1 opt geometry) in nm:': 221.99921189152178,
            'Stokes shift in eV::': -0.034850253288116306,
            'Stokes shift in nm::': 1.3938155330591826
        }
    }

    # Create a temporary YAML file
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_yml:
        yaml.dump(results_yml_content, temp_yml)
        results_yml_path = temp_yml.name

    try:
        # Call function
        get_result_from.QPAnalyzeStokesShift(local_result, results_yml_path)

        # Expected values
        expected_result = {
            'stokes_shift': {
                'value': -0.034850253288116306,
                'results': {
                    'Stokes shift in eV': -0.034850253288116306,
                    'Stokes shift in nm': 1.3938155330591826,
                    'E(S1,S0_opt) in eV': 5.550755161410007,
                    'E(S1,S0_opt) in nm': 223.39302742458096,
                    'E(S1,S1_opt) in eV': 5.585605414698123,
                    'E(S1,S1_opt) in nm': 221.99921189152178
                }
            }
        }

        # Assert values
        assert local_result == expected_result

    finally:
        # Clean up temporary file
        os.remove(results_yml_path)


if __name__ == "__main__":
    pytest.main()