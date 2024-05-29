import yaml
import pathlib


def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


def save_yaml(data, file_path):
    with open(file_path, 'w') as file:
        yaml.safe_dump(data, file)


def update_dict(original_dict, changes_dict):
    for key, value in changes_dict.items():
        if isinstance(value, dict):
            if key not in original_dict or not isinstance(original_dict[key], dict):
                raise KeyError(f"Key '{key}' not found or is not a dictionary in the original dictionary.")
            update_dict(original_dict[key], value)
        else:
            if key not in original_dict:
                raise KeyError(f"Key '{key}' not found in the original dictionary.")
            original_dict[key] = value


def apply_changes(dictionary_path, changes_path, output_path):
    original_dict = load_yaml(dictionary_path)
    changes_dict = load_yaml(changes_path)
    update_dict(original_dict, changes_dict)
    save_yaml(original_dict, output_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Apply changes to a dictionary YAML file.")
    parser.add_argument('--dictionary', type=pathlib.Path, required=True, help="Path to the dictionary YAML file")
    parser.add_argument('--changes', type=pathlib.Path, required=True, help="Path to the changes YAML file")
    parser.add_argument('--output', type=pathlib.Path, required=True, help="Path to save the updated YAML file")
    args = parser.parse_args()

    apply_changes(args.dictionary, args.changes, args.output)
