import yaml


def read_params_from_yaml(yaml_file):
    with open(yaml_file, 'r') as file:
        params = yaml.safe_load(file)
    return params


def build_command(yaml_file):
    params = read_params_from_yaml(yaml_file)

    def add_params_to_command(params, prefix=''):
        command_parts = []
        for key, value in params.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                command_parts.extend(add_params_to_command(value, full_key))
            else:
                command_parts.append(f"{full_key}={value}")
        return command_parts

    command_parts = add_params_to_command(params)
    command = "Deposit " + " ".join(command_parts)
    return command
