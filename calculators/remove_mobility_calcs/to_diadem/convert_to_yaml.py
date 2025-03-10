"""
Converts
"""

import os
import re
import sys


def convert_to_yaml_format(text):
    # Replace 'key. value' pattern with 'key: value' (ignoring numbers or files)
    yaml_text = re.sub(r'(\s*)(\w+)\.\s+', r'\1\2: ', text)  # Replace dots in key-value pairs with colons
    return yaml_text


def main():
    # Check if the input file name is passed as a command-line argument
    if len(sys.argv) != 2:
        print("Usage: python convert_to_yaml.py <input_file>")
        sys.exit(1)

    # Get the input file from the command-line argument
    input_file = sys.argv[1]

    # Ensure the input file exists
    if not os.path.exists(input_file):
        print(f"Error: The file {input_file} does not exist.")
        sys.exit(1)

    # Get the base name of the input file and change the extension to .yml
    base_name = os.path.splitext(input_file)[0]
    output_file = f"{base_name}.yml"

    # Read the content of the input file
    with open(input_file, 'r') as file:
        content = file.read()

    # Convert the content to proper YAML format
    yaml_content = convert_to_yaml_format(content)

    # Write the YAML content to a new file with the same base name and .yml extension
    with open(output_file, 'w') as output_file:
        output_file.write(yaml_content)

    print(f"Converted content saved to {output_file.name}")


if __name__ == "__main__":
    main()
