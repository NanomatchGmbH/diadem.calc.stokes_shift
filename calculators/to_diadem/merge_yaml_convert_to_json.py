import yaml
import json
import os
import argparse


def merge_yaml_to_json(input_folder):
    yaml_folder = os.path.join(input_folder, 'yaml')
    json_folder = os.path.join(input_folder, 'json')

    # Ensure the output JSON folder exists
    if not os.path.exists(json_folder):
        os.makedirs(json_folder)

    # Create the path for the output JSON file
    output_json_path = os.path.join(json_folder, 'merged_data.json')

    all_data = {}
    index = 0

    # Iterate over all YAML files
    for yaml_file in os.listdir(yaml_folder):
        if yaml_file.endswith('.yml'):
            yaml_path = os.path.join(yaml_folder, yaml_file)

            # Load YAML content
            with open(yaml_path, 'r') as file:
                yaml_content = yaml.safe_load(file)

            # Add the YAML content to the JSON structure, using index as key
            all_data[str(index)] = yaml_content
            index += 1

    # Write the merged data into the final JSON file
    with open(output_json_path, 'w') as json_file:
        json.dump(all_data, json_file, indent=4)

    print(f"Merged YAML files into {output_json_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Merge YAML files to a single JSON file.')
    parser.add_argument('input_folder', type=str, help='The base folder (e.g., to_diadem).')

    args = parser.parse_args()

    merge_yaml_to_json(args.input_folder)
