# context_managers.py

import os
import pathlib
import structlog

# Create a logger
logger = structlog.get_logger()


class ChangeDirectory:
    """
    Context manager for creating and changing the current working directory to a simulations directory.
    If you want to provide an additional parameter to the inner make it with additional_parameter.
    It will, however, rename your directory:
    <dir_name> --> <dir_name>_<additional_parameter>
    Example:
        Lightforge --> Lightforge_hole
    """

    def __init__(self, dir_name, additional_parameter=None):
        self.dir_name = f"{dir_name}_{additional_parameter}" if additional_parameter else dir_name
        self.new_path = pathlib.Path.cwd() / self.dir_name
        self.original_path = pathlib.Path.cwd()
        self.additional_parameter = additional_parameter

    def __enter__(self):
        logger.info(f"{self.dir_name} starts . . .")
        self.new_path.mkdir(exist_ok=True)
        os.chdir(self.new_path)
        logger.info(f"Changed directory to {self.new_path}")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.original_path)
        logger.info(f". . . {self.dir_name} successful!")
        logger.info(f"Returned to original directory {self.original_path}")
