import yaml
import structlog
from .logging_config import configure_logging
import os
import shutil

# Ensure the logging configuration is applied
configure_logging()

# Get the logger
logger = structlog.get_logger()

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


def save_yaml(data, file_path):
    with open(file_path, 'w') as file:
        yaml.safe_dump(data, file)


def rename_dir(src_dir, new_dir_name):
    cwd = os.getcwd()
    src_path = os.path.join(cwd, src_dir)
    dest_path = os.path.join(cwd, new_dir_name)

    if not os.path.exists(src_path):
        logger.error(f"The directory {src_dir} does not exist in the current working directory.")
        return

    if os.path.exists(dest_path):
        logger.error(f"The directory {new_dir_name} already exists in the current working directory.")
        return

    shutil.move(src_path, dest_path)
    logger.info(f"Moved directory {src_dir} to {new_dir_name}")