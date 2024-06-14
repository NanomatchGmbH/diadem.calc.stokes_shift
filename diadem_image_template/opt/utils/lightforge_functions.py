import yaml
from .logging_config import configure_logging
import structlog

# Ensure the logging configuration is applied
configure_logging()

# Get the logger
logger = structlog.get_logger()


def set_carrier_type(destination_path, carrier_type):
    """
    Update the YAML configuration file to set the carrier type to either 'hole' or 'electron'.

    Parameters:
    destination_path (str): Path to the YAML settings file.
    carrier_type (str): The carrier type, either 'hole' or 'electron'.
    """
    with open(destination_path, 'r') as file:
        config = yaml.safe_load(file)

    if carrier_type == 'hole':
        config['particles']['holes'] = True
        config['particles']['electrons'] = False
        for experiment in config['experiments']:
            experiment['initial_holes'] = experiment.pop('initial_electrons', 30)  # Remove initial_electrons if present
    elif carrier_type == 'electron':
        config['particles']['holes'] = False
        config['particles']['electrons'] = True
        for experiment in config['experiments']:
            experiment['initial_electrons'] = experiment.pop('initial_holes', 30)  # Remove initial_holes if present
    else:
        raise ValueError("carrier_type must be either 'hole' or 'electron'")

    with open(destination_path, 'w') as file:
        yaml.safe_dump(config, file)

    logger.info(f"Updated carrier type to {carrier_type} in {destination_path}")
