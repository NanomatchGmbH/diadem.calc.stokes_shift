import yaml
from .logging_config import configure_logging
import structlog
import glob
import os

# Ensure the logging configuration is applied
configure_logging()

# Get the logger
logger = structlog.get_logger()


def rename_file(input_pattern, new_filename):
    # Use glob to find files matching the pattern
    files = glob.glob(input_pattern)

    # Check if there is exactly one file matching the pattern
    if len(files) != 1:
        logger.error("Expected exactly one file matching the pattern", pattern=input_pattern, found=len(files))
        raise FileNotFoundError(
            f"Expected exactly one file matching the pattern '{input_pattern}', but found {len(files)}.")

    # Get the file path
    original_file = files[0]

    # Define the new file path
    new_file = os.path.join(os.path.dirname(original_file), new_filename)

    # Rename the file
    os.rename(original_file, new_file)
    logger.info("File renamed", original_file=original_file, new_file=new_file)