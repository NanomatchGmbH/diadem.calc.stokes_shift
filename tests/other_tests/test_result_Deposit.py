import pytest
from diadem_image_template.opt.utils.result import get_result_from

@pytest.fixture
def local_result_template():
    return {
        "morphology": {
            "value": "file: structure.cml",
            "results": {
                "mass_density": {
                    "value": None,
                    "unit": "g/cm3",
                    "std": None
                },
                "number_density": {
                    "value": None,
                    "unit": "1/cm3",
                    "std": None
                },
                "molecular_volume": {
                    "value": None,
                    "unit": "nm3"
                },
                "rdf_first_peak": {
                    "value": None,
                    "unit": "Angstrom"
                },
                "average_neighbors": {
                    "value": None,
                    "unit": "Angstrom"
                }
            }
        }
    }


def test_deposit(local_result_template):
    get_result_from.Deposit(local_result_template, 'inputs/DensityAnalysis.out')

    print(local_result_template)

    assert local_result_template["morphology"]["results"]["mass_density"]["value"] == 1.13
    assert local_result_template["morphology"]["results"]["mass_density"]["std"] == 0.01
    assert local_result_template["morphology"]["results"]["number_density"]["value"] == 4.40e+21
    assert local_result_template["morphology"]["results"]["number_density"]["std"] == 1.43e+20
    assert local_result_template["morphology"]["results"]["molecular_volume"]["value"] == 0.23
    assert local_result_template["morphology"]["results"]["rdf_first_peak"]["value"] == 5.297805642633229
    assert local_result_template["morphology"]["results"]["average_neighbors"]["value"] == 19.8