import pytest
from diadem_image_template.opt.utils.result import get_result_from
import numpy as np

@pytest.fixture
def local_result_template():
    return {
        "hole_mobility": {
            "value": None,
            "results": {
                "fields": {
                    "values": [],
                    "units": "V/nm"
                },
                "mobilities": {
                    "values": [],
                    "units": "cm²/V·s"
                },
                "stderr": {
                    "values": [],
                    "units": "cm²/V·s"
                }
            }
        },
        "electron_mobility": {
            "value": None,
            "results": {
                "fields": {
                    "values": [],
                    "units": "V/nm"
                },
                "mobilities": {
                    "values": [],
                    "units": "cm²/V·s"
                },
                "stderr": {
                    "values": [],
                    "units": "cm²/V·s"
                }
            }
        }
    }


def test_lightforge(local_result_template):
    mobilities_file = "inputs/mobilities_all_fields.dat"
    settings_file = "inputs/settings"


    # Run the lightforge function
    get_result_from.lightforge(local_result_template, str(mobilities_file), str(settings_file), hole_or_electron='hole')
    get_result_from.lightforge(local_result_template, str(mobilities_file), str(settings_file), hole_or_electron='electron')

    # Print the result for debugging
    print(local_result_template)

    # Assert the expected values
    for hole_or_electron in ['hole', 'electron']:
        hole_or_electron_mobility = f'{hole_or_electron}_mobility'
        assert local_result_template[hole_or_electron_mobility]["results"]["fields"]["values"] == [0.2, 0.3, 0.4]
        assert local_result_template[hole_or_electron_mobility]["results"]["mobilities"]["values"] == pytest.approx([
            1.186932741712129827e-02, 2.732111808085449511e-02, 3.904151254044361391e-02
        ], rel=1e-6)
        assert local_result_template[hole_or_electron_mobility]["results"]["stderr"]["values"] == pytest.approx([
            2.157156189860654893e-03/np.sqrt(10), 8.981448462374695338e-03/np.sqrt(10), 1.049719255916519572e-02 / np.sqrt(10)
        ], rel=1e-6)
        assert local_result_template[hole_or_electron_mobility]["value"] is not None  # Check if zero-field mobility is set


if __name__ == "__main__":
    pytest.main()
