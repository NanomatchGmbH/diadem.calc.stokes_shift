import pytest
import yaml
import numpy as np
from diadem_image_template.opt.utils.result import get_result_from


@pytest.fixture
def local_result_template():
    return {
        "HOMO": {"value": None},
        "LUMO": {"value": None},
        "dipole": {
            "value": None,
            "results": {
                "dipole_vector": [None, None, None]
            }
        }
    }


def test_QPParametrizer(local_result_template, tmpdir):
    # Create a temporary YAML file for testing
    yaml_content = {
        'homo energy': -5.2,
        'lumo energy': -2.3,
        'dipole': [1.0, 2.0, 2.0]
    }

    yaml_file = tmpdir.join("test.yml")
    with open(yaml_file, 'w') as file:
        yaml.dump(yaml_content, file)

    # Run the QPParametrizer function
    get_result_from.QPParametrizer(local_result_template, str(yaml_file))

    # Assert the expected values
    assert local_result_template["HOMO"]["value"] == -5.2
    assert local_result_template["LUMO"]["value"] == -2.3
    assert local_result_template["dipole"]["value"] == pytest.approx(np.sqrt(1.0 ** 2 + 2.0 ** 2 + 2.0 ** 2))
    assert local_result_template["dipole"]["results"]["dipole_vector"] == [1.0, 2.0, 2.0]


if __name__ == "__main__":
    pytest.main()