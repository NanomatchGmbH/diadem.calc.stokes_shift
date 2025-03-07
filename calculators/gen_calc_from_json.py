import argparse
import json
import yaml
import pathlib
import sys

def json_to_yaml(json_filepath):
    # Determine the YAML file path
    yml_filepath = json_filepath.with_suffix('.yml')
    
    # Read the JSON file
    with open(json_filepath, 'r') as json_file:
        data = json.load(json_file)
    
    # Write the data to a YAML file
    with open(yml_filepath, 'w') as yml_file:
        yml.dump(data, yml_file, default_flow_style=False)
    
    print(f"Converted {json_filepath} to {yml_filepath}")

def main():
    # Set up the argument parser
    parser = argparse.ArgumentParser(description="Convert a JSON file to a YAML file.")
    parser.add_argument('json_file', type=str, help="The path to the JSON file to be converted.")
    
    # Parse the arguments
    args = parser.parse_args()

    # Convert the JSON file to a YAML file
    json_filepath = pathlib.Path(args.json_file)
    if not json_filepath.is_file():
        print(f"Error: The file {args.json_file} does not exist.")
        sys.exit(1)
    
    json_to_yml(json_filepath)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python json_to_yml.py <json_file>")
        sys.exit(1)
    main()
