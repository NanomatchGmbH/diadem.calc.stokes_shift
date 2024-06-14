import pathlib
import shutil
import glob
import logging

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)  # Adjust as needed for your use case

def create_output_directory_and_copy_files(required_files, output_dir='out'):
    """
    Create an output directory and copy the required files into it.

    Parameters:
    required_files (list): List of file paths to be copied, with support for wildcards.
    output_dir (str): Name of the output directory.
    """
    # Create the output directory using pathlib
    output_dir_path = pathlib.Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Copy the required files to the output directory
    for pattern in required_files:
        matched_files = glob.glob(pattern)
        if not matched_files:
            logger.critical(f"No files matched the pattern: {pattern}")
            raise FileNotFoundError(f"No files matched the pattern: {pattern}")
        for file in matched_files:
            file_path = pathlib.Path(file)
            shutil.copy(file_path, output_dir_path)

    # Return the absolute path of the output directory
    return str(output_dir_path.resolve())

def check_required_output_files_exist(filepaths, description="file"):
    """
    Check if a file or list of files exists in the current working directory and log a critical error if any are missing.
    Raise a FileNotFoundError if any file is not found.
    Treat filenames with wildcards (e.g., "Delta_*.png") by finding all files that match the pattern.
    """
    if isinstance(filepaths, (str, pathlib.Path)):
        filepaths = [filepaths]

    cwd = pathlib.Path.cwd()
    missing_files = []

    for pattern in filepaths:
        matched_files = glob.glob(str(cwd / pattern))
        if not matched_files:
            missing_files.append(str(pattern))

    if missing_files:
        logger.critical(f"Required {description}(s) missing in current working directory: {', '.join(missing_files)}")
        raise FileNotFoundError(
            f"Required {description}(s) missing in current working directory: {', '.join(missing_files)}")

# Example usage
required_files = ['inputs/file1.txt', 'inputs/file2.txt', 'inputs/Analysis/energy/DeltaE_*.png']
output_dir = 'out'
absolute_output_path = create_output_directory_and_copy_files(required_files, output_dir)
print(f"The absolute path of the output directory is: {absolute_output_path}")

# Check if the required files exist
try:
    check_required_output_files_exist(required_files)
except FileNotFoundError as e:
    print(e)