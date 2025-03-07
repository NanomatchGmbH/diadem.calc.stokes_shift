from diadem_image_template.opt.utils.build_command_from_yml import build_command


def test_generate_command_from_yaml():
    yaml_file = 'inputs/deposit_cargs.yml'

    # Build the Deposit command
    command = build_command(yaml_file)

    print("Generated Command:")
    print(command)


if __name__ == "__main__":
    test_generate_command_from_yaml()