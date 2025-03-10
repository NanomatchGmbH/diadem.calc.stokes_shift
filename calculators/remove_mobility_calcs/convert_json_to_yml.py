import json
import yaml
import argparse
import os

# Set up argument parsing
parser = argparse.ArgumentParser(description='Convert JSON to YAML.')
parser.add_argument('input_file', help='The input JSON file')

args = parser.parse_args()

# Determine the output file name based on the input file's base name
base_name = os.path.splitext(args.input_file)[0]
output_file = f"{base_name}.yml"

# Read the JSON file
with open(args.input_file, 'r') as json_file:
    data = json.load(json_file)

# Write the YAML file
with open(output_file, 'w') as yaml_file:
    yaml.dump(data, yaml_file, default_flow_style=False)

print(f"Conversion complete: {args.input_file} -> {output_file}")

