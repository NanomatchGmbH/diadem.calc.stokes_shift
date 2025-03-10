"""
This will create the json files that are to be used as:

"""

import os
import sys
import yaml
import json
import re

def parse_list_calculators(list_calculators_file, version):
    # Read the list_calculators.txt file and split by chunks (based on the "1.", "2." pattern)
    calculators = {}
    with open(list_calculators_file, 'r') as f:
        content = f.read()

    # Use regex to split by lines starting with numbers (e.g., "1.", "2.", etc.)
    calculator_chunks = re.split(r'^\d+\.', content, flags=re.MULTILINE)

    for chunk in calculator_chunks:
        if "version:" in chunk:
            current_calculator = {}
            version_match = re.search(r'version:\s*([\d\.]+)', chunk)
            if version_match and version_match.group(1) == version:
                # Extract relevant fields from each chunk
                calculator_id_match = re.search(r'calculatorId:\s*([^\n]+)', chunk)
                id_match = re.search(r'id:\s*([^\n]+)', chunk)
                provides_match = re.findall(r'-\s*([^\n]+)', chunk)
                
                if calculator_id_match and id_match:
                    current_calculator["calculatorId"] = calculator_id_match.group(1).strip()
                    current_calculator["id"] = id_match.group(1).strip()
                    current_calculator["provides"] = provides_match if provides_match else []
                    calculators[current_calculator["calculatorId"]] = current_calculator

    return calculators


def parse_list_pcs(list_pcs_file):
    # Parse list_pcs.txt to get the name and equivalentNames
    pcs_map = {}
    with open(list_pcs_file, 'r') as f:
        content = f.read()

    # Use regex to split by chunks for each property (starts with digits)
    property_chunks = re.split(r'^\d+\.', content, flags=re.MULTILINE)

    for chunk in property_chunks:
        name_match = re.search(r'name:\s*([^\n]+)', chunk)
        equivalent_names_match = re.search(r'equivalentNames:\s*\[([^\]]*)\]', chunk)

        if name_match:
            name = name_match.group(1).strip().lower()  # Normalize to lowercase
            if equivalent_names_match:
                # Clean up quotes and spaces from the equivalentNames
                equivalent_names = [name.strip().strip("'\"") for name in equivalent_names_match.group(1).split(',')]
            else:
                equivalent_names = [name]  # If no equivalentNames, default to name itself

            pcs_map[name] = equivalent_names

    return pcs_map

def create_json_files_for_provides(calculators, pcs_map, yaml_folder, output_folder):
    # For every calculator, extract the provides and create a JSON file for each property
    provides_map = {}

    # Read YAML files to find matching calculators and their provides
    for yaml_file in os.listdir(yaml_folder):
        if yaml_file.endswith(".yml"):
            with open(os.path.join(yaml_folder, yaml_file), 'r') as f:
                yaml_content = yaml.safe_load(f)
                calculator_id = yaml_content.get("calculatorId", None)
                provides = yaml_content.get("provides", [])

                if calculator_id and calculator_id in calculators:
                    calculator_id = calculators[calculator_id]["id"]
                    for provide in provides:
                        provide_normalized = provide.strip().lower()  # Normalize to lowercase
                        if provide_normalized not in pcs_map:
                            raise Exception(f"Property '{provide}' not found in PCT list. Add it to PCT first.")
                        
                        if provide not in provides_map:
                            provides_map[provide] = []
                        provides_map[provide].append(calculator_id)

    # Create JSON files for each property (provide key)
    for provide, calc_refs in provides_map.items():
        provide_normalized = provide.strip().lower()
        equivalent_names = pcs_map.get(provide_normalized, [provide])  # Get equivalentNames or default to provide name
        output_json = {
            "name": provide,
            "calcRef": calc_refs,
            "equivalentNames": equivalent_names
        }

        # Save JSON to file
        json_filename = os.path.join(output_folder, f"{provide}.json")
        with open(json_filename, 'w') as json_file:
            json.dump(output_json, json_file, indent=4)
        print(f"Created {json_filename}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python yaml_to_json.py <folder_name>")
        sys.exit(1)

    folder_name = sys.argv[1]

    # Define the paths based on the folder name
    base_folder = os.path.join(os.getcwd(), folder_name)
    list_calculators_file = os.path.join(base_folder, 'txt', 'list_calculators.txt')
    list_pcs_file = os.path.join(base_folder, 'txt', 'list_pct.txt')
    yaml_folder = os.path.join(base_folder, 'yaml')
    output_folder = os.path.join(base_folder, 'json/update_dicts')

    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Version to filter by
    version = "2.0.2"  # idle?

    # Parse the list_calculators.txt file and get calculators for the given version
    calculators = parse_list_calculators(list_calculators_file, version)

    # Parse the list_pcs.txt to get name and equivalentNames
    pcs_map = parse_list_pcs(list_pcs_file)

    # Generate JSON files for each provide key
    create_json_files_for_provides(calculators, pcs_map, yaml_folder, output_folder)

