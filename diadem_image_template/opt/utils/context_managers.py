# context_managers.py

import os
import pathlib
import structlog
import time

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
        self.start_time = None  # Add a variable to store the start time

    def __enter__(self):
        logger.info(f"{self.dir_name} starts . . .")
        self.new_path.mkdir(exist_ok=True)
        os.chdir(self.new_path)
        logger.info(f"Changed directory to {self.new_path}")
        self.start_time = time.time()  # Start timing here
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        elapsed_time = time.time() - self.start_time  # Calculate elapsed time

        # time in hours minutes seconds: __h__m__s
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        readable_time = f"{int(hours):02}h{int(minutes):02}m{int(seconds):02}s"
        logger.info(f"{self.dir_name} completed in {readable_time}.")

        os.chdir(self.original_path)
        logger.info(f". . . {self.dir_name} successful!")
        logger.info(f"Returned to original directory {self.original_path}")