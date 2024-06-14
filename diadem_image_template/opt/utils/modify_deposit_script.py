import os
import shutil


def copy_deposit_init_with_changes(source_script, changes, output):
    # Read the source script
    with open(source_script, 'r') as file:
        script_content = file.read()

    # Find the Deposit command line
    deposit_line_start = script_content.find("Deposit ")
    deposit_line_end = script_content.find("\n", deposit_line_start)
    deposit_line = script_content[deposit_line_start:deposit_line_end]

    # Split the Deposit command into parts
    deposit_parts = deposit_line.split()

    # Build the new parameters string from the dictionary
    new_params = {}
    for key, value in changes.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                if isinstance(subvalue, dict):
                    for subsubkey, subsubvalue in subvalue.items():
                        new_params[f"{key}.{subkey}.{subsubkey}"] = subsubvalue
                else:
                    new_params[f"{key}.{subkey}"] = subvalue
        else:
            new_params[key] = value

    # Update the deposit parts with new parameters
    for i in range(1, len(deposit_parts)):
        param, _, _ = deposit_parts[i].partition("=")
        if param in new_params:
            deposit_parts[i] = f"{param}={new_params[param]}"
            new_params.pop(param, None)

    # Append any new parameters not originally in the command
    for key, value in new_params.items():
        deposit_parts.append(f"{key}={value}")

    new_deposit_line = " ".join(deposit_parts)
    modified_script_content = script_content[:deposit_line_start] + new_deposit_line + script_content[deposit_line_end:]

    # Write the modified script to the target location
    with open(output, 'w') as file:
        file.write(modified_script_content)
