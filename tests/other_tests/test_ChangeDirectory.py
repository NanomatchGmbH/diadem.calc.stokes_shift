# test_change_directory.py

import pathlib
import os
import shutil
from diadem_image_template.opt.utils.context_managers import ChangeDirectory  # Import the ChangeDirectory class


def test_change_directory():
    # Create a temporary directory for testing
    temp_dir = pathlib.Path('temp_test_dir')
    temp_dir.mkdir(exist_ok=True)

    # Save the original working directory
    original_cwd = pathlib.Path.cwd()

    # Test without additional parameter
    try:
        with ChangeDirectory(temp_dir / 'test_without_param') as cd:
            assert pathlib.Path.cwd() == cd.new_path, "Directory did not change correctly without parameter"
            assert cd.additional_parameter is None, "additional_parameter should be None"
            print(f"Test without additional parameter passed. Current directory: {pathlib.Path.cwd()}")

    except Exception as e:
        print(f"Test without additional parameter failed: {e}")

    finally:
        os.chdir(original_cwd)

    # Cleanup
    shutil.rmtree(temp_dir / 'test_without_param', ignore_errors=True)

    # Test with additional parameter
    try:
        with ChangeDirectory(temp_dir / 'test_with_param', additional_parameter='hole') as cd:
            expected_path = temp_dir / 'test_with_param_hole'
            assert pathlib.Path.cwd() == expected_path, "Directory did not change correctly with parameter"
            assert cd.additional_parameter == 'hole', "additional_parameter should be 'hole'"
            print(f"Test with additional parameter passed. Current directory: {pathlib.Path.cwd()}")

    except Exception as e:
        print(f"Test with additional parameter failed: {e}")

    finally:
        os.chdir(original_cwd)

    # Cleanup
    shutil.rmtree(temp_dir / 'test_with_param_hole', ignore_errors=True)

    # Final cleanup of temporary directory
    shutil.rmtree(temp_dir, ignore_errors=True)


# Run the tests
test_change_directory()
