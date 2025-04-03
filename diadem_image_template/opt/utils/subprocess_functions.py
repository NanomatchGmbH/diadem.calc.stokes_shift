from .logging_config import configure_logging
import structlog
import subprocess
import shlex

# Ensure the logging configuration is applied
configure_logging()

# Get the logger
logger = structlog.get_logger()


def run_command(command, use_shell=False, stdout_file=None, stderr_file=None, combine_output=False):
    """
    Run a shell command and optionally redirect stdout/stderr to files.

    Parameters:
        command (str or list): The command to run.
        use_shell (bool): Whether to execute using the shell.
        stdout_file (str): Path to file to write stdout.
        stderr_file (str): Path to file to write stderr.
        combine_output (bool): If True, redirect stderr to stdout file.
    """
    try:
        logger.info("Running command", command=command)

        # Prepare the command
        cmd = command if use_shell else (shlex.split(command) if isinstance(command, str) else command)

        # Open file handles if needed
        with open(stdout_file, 'w') if stdout_file else subprocess.PIPE as stdout_stream, \
                open(stderr_file, 'w') if stderr_file and not combine_output else (
                        stdout_stream if combine_output and stdout_file else subprocess.PIPE
                ) as stderr_stream:

            result = subprocess.run(
                cmd,
                shell=use_shell,
                check=True,
                stdout=stdout_stream,
                stderr=stderr_stream,
                encoding='utf8'
            )

        if stdout_file:
            logger.info(f"Command stdout written to {stdout_file}")
        elif result.stdout:
            logger.info(f"Command stdout: {result.stdout}")

        if stderr_file and not combine_output:
            logger.info(f"Command stderr written to {stderr_file}")
        elif result.stderr:
            logger.error(f"Command stderr: {result.stderr}")

    except subprocess.CalledProcessError as e:
        logger.error("Command failed", command=command, returncode=e.returncode, output=e.output, stderr=e.stderr)
        raise
    except FileNotFoundError as e:
        logger.error(f"Command not found: {e.filename}", error=str(e))
        raise
