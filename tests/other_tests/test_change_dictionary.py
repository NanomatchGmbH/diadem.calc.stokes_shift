import pytest
import yaml
from change_dictionary import update_dict


def test_update_dict():
    original_dict = {
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
        'DFT Engine': {
            'Threads': '30',
            'Memory (MB)': 78000.0,
            'PySCF Settings': {
                'basis': 'def2-SVP'
            }
        }
    }

    expected_dict = {
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


if __name__ == "__main__":
    pytest.main()
