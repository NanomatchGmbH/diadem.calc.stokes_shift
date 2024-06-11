import pytest
import yaml
import sys
import os

# We test the module that is a part of the image: diadem_image_template/opt/utils/change_dictionary.py
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from diadem_image_template.opt.utils.change_dictionary import update_dict


def test_update_dict():
    original_dict = {
        'Some list': [{'first': 1}, {'second': 2}, {'third': 3}],
        'DFT Engine': {
            'Engine': 'Psi4',
            'Memory (MB)': 16000.0,
            'Threads': '4',
            'PySCF Settings': {
                'basis': 'def2-SVP',
                'functional': 'B3LYP',
                'Partial Charge Method': 'ESP',
                'Preoptimization': 'None',
                'gridsize': 'fast'
            }
        }
    }

    changes_dict = {
        'Some list': [{'first': 1.1}],
        'DFT Engine': {
            'Threads': '30',
            'Memory (MB)': 78000.0,
            'PySCF Settings': {
                'basis': 'def2-SVP'
            }
        }
    }

    expected_dict = {
        'Some list': [{'first': 1.1}, {'second': 2}, {'third': 3}],
        'DFT Engine': {
            'Engine': 'Psi4',
            'Memory (MB)': 78000.0,
            'Threads': '30',
            'PySCF Settings': {
                'basis': 'def2-SVP',
                'functional': 'B3LYP',
                'Partial Charge Method': 'ESP',
                'Preoptimization': 'None',
                'gridsize': 'fast'
            }
        }
    }

    update_dict(original_dict, changes_dict)
    assert original_dict == expected_dict


def test_key_not_found():
    original_dict = {
        'DFT Engine': {
            'Engine': 'Psi4',
            'Memory (MB)': 16000.0,
            'Threads': '4'
        }
    }

    changes_dict = {
        'DFT Engine': {
            'Threads': '30',
            'NonExistentKey': 'value'
        }
    }

    with pytest.raises(KeyError):
        update_dict(original_dict, changes_dict)


def test_update_lf():
    original_dict = {
        'pbc': [True, True, True],
        'expansion_scheme': 'edcm',
        'particles': {
            'holes': True,
            'electrons': False,
            'excitons': False
        },
        'morphology_width': 40,
        'QP_output_files': [
            {
                'name': 'molA',
                'QP_output.zip': 'QP_output_0.zip'
            }
        ],
        'materials': [
            {
                'name': 'htl',
                'input_mode_transport': "QP: sig PAR: eaip,l",
                'molecule_parameters': {
                    'molecule_pdb': 'molecule_0.pdb',
                    'QP_output_sigma': 'molA',
                    'energies': [
                        [5.0, 2.0],
                        [0.2, 0.2]
                    ]
                }
            }
        ],
        'layers': [
            {
                'thickness': 40,
                'morphology_input_mode': 'automatic',
                'molecule_species': [
                    {
                        'material': 'htl',
                        'concentration': 1.0
                    }
                ]
            }
        ],
        'neighbours': 120,
        'transfer_integral_source': 'QP_output',
        'superexchange': True,
        'pair_input': [
            {
                'molecule 1': 'htl',
                'molecule 2': 'htl',
                'QP_output': 'molA'
            }
        ],
        'experiments': [
            {
                'simulations': 10,
                'measurement': 'DC',
                'Temperature': 300,
                'field_direction': [1, 0, 0],
                'field_strength': '0.02 0.03 0.04',
                'initial_holes': 30
            }
        ],
        'iv_fluctuation': 0.05,
        'new_wano': True,
        'max_iterations': 500000,
        'ti_prune': True,
        'live_reporting': {
            'reporting_time_interval': 15,
            'IV': False,
            'density': False
        }
    }

    changes_dict = {
        'morphology_width': 30,
        'layers': [
            {
                'thickness': 30
            }
        ],
        'experiments': [
            {
                'simulations': 10,
                'Temperature': 300,
                'field_strength': '0.2 0.3 0.4'
            }
        ],
        'iv_fluctuation': 0.05,
        'max_iterations': 500000
    }

    expected_dict = {
        'pbc': [True, True, True],
        'expansion_scheme': 'edcm',
        'particles': {
            'holes': True,
            'electrons': False,
            'excitons': False
        },
        'morphology_width': 30,
        'QP_output_files': [
            {
                'name': 'molA',
                'QP_output.zip': 'QP_output_0.zip'
            }
        ],
        'materials': [
            {
                'name': 'htl',
                'input_mode_transport': "QP: sig PAR: eaip,l",
                'molecule_parameters': {
                    'molecule_pdb': 'molecule_0.pdb',
                    'QP_output_sigma': 'molA',
                    'energies': [
                        [5.0, 2.0],
                        [0.2, 0.2]
                    ]
                }
            }
        ],
        'layers': [
            {
                'thickness': 30,
                'morphology_input_mode': 'automatic',
                'molecule_species': [
                    {
                        'material': 'htl',
                        'concentration': 1.0
                    }
                ]
            }
        ],
        'neighbours': 120,
        'transfer_integral_source': 'QP_output',
        'superexchange': True,
        'pair_input': [
            {
                'molecule 1': 'htl',
                'molecule 2': 'htl',
                'QP_output': 'molA'
            }
        ],
        'experiments': [
            {
                'simulations': 10,
                'measurement': 'DC',
                'Temperature': 300,
                'field_direction': [1, 0, 0],
                'field_strength': '0.2 0.3 0.4',
                'initial_holes': 30
            }
        ],
        'iv_fluctuation': 0.05,
        'new_wano': True,
        'max_iterations': 500000,
        'ti_prune': True,
        'live_reporting': {
            'reporting_time_interval': 15,
            'IV': False,
            'density': False
        }
    }

    update_dict(original_dict, changes_dict)
    assert original_dict == expected_dict


if __name__ == "__main__":
    pytest.main()
