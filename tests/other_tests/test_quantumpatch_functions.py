import pytest
import os
import tempfile
import shutil
from diadem_image_template.opt.utils.quantumpatch_functions import rename_file


@pytest.fixture
def setup_test_files():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    # Create a temporary file that matches the pattern
    original_file = os.path.join(temp_dir, 'DeltaE123.png')
    os.makedirs(os.path.join(temp_dir, 'Analysis/energy'), exist_ok=True)
    test_file = os.path.join(temp_dir, 'Analysis/energy/DeltaE123.png')
    with open(test_file, 'w') as f:
        f.write('test content')

    yield temp_dir, test_file

    # Cleanup: remove the temporary directory and all its contents
    shutil.rmtree(temp_dir)

def test_rename_file_success(setup_test_files):
    temp_dir, test_file = setup_test_files
    new_filename = 'DeltaE.png'

    # Run the rename_file function
    rename_file(os.path.join(temp_dir, 'Analysis/energy/DeltaE*.png'), os.path.join(temp_dir, 'Analysis/energy/DeltaE.png'))

    # Verify the file was renamed correctly
    new_file = os.path.join(temp_dir, 'Analysis/energy/DeltaE.png')
    assert os.path.isfile(new_file)
    assert not os.path.isfile(test_file)

def test_rename_file_multiple_files(setup_test_files):
    temp_dir, test_file = setup_test_files
    new_filename = 'DeltaE.png'

    # Create another file that matches the pattern
    another_file = os.path.join(temp_dir, 'Analysis/energy/DeltaE456.png')
    with open(another_file, 'w') as f:
        f.write('test content')

    # Run the rename_file function and expect a FileNotFoundError
    with pytest.raises(FileNotFoundError):
        rename_file(os.path.join(temp_dir, 'Analysis/energy/DeltaE*.png'), os.path.join(temp_dir, 'Analysis/energy/DeltaE.png'))

def test_rename_file_no_match(setup_test_files):
    temp_dir, test_file = setup_test_files
    new_filename = 'DeltaE.png'

    # Remove the test file to simulate no match
    os.remove(test_file)

    # Run the rename_file function and expect a FileNotFoundError
    with pytest.raises(FileNotFoundError):
        rename_file(os.path.join(temp_dir, 'Analysis/energy/DeltaE*.png'), os.path.join(temp_dir, 'Analysis/energy/DeltaE.png'))

if __name__ == "__main__":
    pytest.main()