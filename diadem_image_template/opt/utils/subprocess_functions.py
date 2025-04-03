from .logging_config import configure_logging
import structlog
import subprocess
import shlex

# Ensure the logging configuration is applied
configure_logging()

# Get the logger
logger = structlog.get_logger()


def run_command(command, use_shell=False, stdout_file=None, stderr_file=None):
    """
    Run a shell command and log its output using structlog.
    Optionally redirect stdout and stderr to output files.
    """
    try:
        logger.info(f"Running command: {command}")

        if use_shell:
            if stdout_file or stderr_file:
                with open(stdout_file, 'w') if stdout_file else subprocess.DEVNULL as out_file, \
                     open(stderr_file, 'w') if stderr_file else subprocess.PIPE as err_file:

                    result = subprocess.run(
                        command,
                        check=True,
                        stdout=out_file,
                        stderr=err_file,
                        shell=True,
                        encoding='utf8'
                    )

                    if stdout_file:
                        logger.info(f"Command stdout written to {stdout_file}")
                    if stderr_file:
                        logger.info(f"Command stderr written to {stderr_file}")
                    elif result.stderr:
                        logger.error(f"Command stderr: {result.stderr}")
            else:
                result = subprocess.run(
                    command,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    encoding='utf8'
                )
                if result.stdout:
                    logger.info(f"Command stdout: {result.stdout}")
                if result.stderr:
                    logger.error(f"Command stderr: {result.stderr}")
        else:
            command_list = shlex.split(command) if isinstance(command, str) else command
            if stdout_file or stderr_file:
                with open(stdout_file, 'w') if stdout_file else subprocess.DEVNULL as out_file, \
                     open(stderr_file, 'w') if stderr_file else subprocess.PIPE as err_file:

                    result = subprocess.run(
                        command_list,
                        check=True,
                        stdout=out_file,
                        stderr=err_file,
                        encoding='utf8'
                    )

                    if stdout_file:
                        logger.info(f"Command stdout written to {stdout_file}")
                    if stderr_file:
                        logger.info(f"Command stderr written to {stderr_file}")
                    elif result.stderr:
                        logger.error(f"Command stderr: {result.stderr}")
            else:
                result = subprocess.run(
                    command_list,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf8'
                )
                if result.stdout:
                    logger.info(f"Command stdout: {result.stdout}")
                if result.stderr:
                    logger.error(f"Command stderr: {result.stderr}")

    except subprocess.CalledProcessError as e:
        logger.error("Command failed", command=command, returncode=e.returncode, output=e.output, stderr=e.stderr)
        raise
    except FileNotFoundError as e:
        logger.error(f"Command not found: {e.filename}", error=str(e))
        raise
