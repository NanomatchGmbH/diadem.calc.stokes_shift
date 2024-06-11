import pathlib
from typing import Union, Dict, Any, Optional
from .general import load_yaml, save_yaml


def update_dict(original, changes):
    for key, value in changes.items():
        if isinstance(value, dict):
            if key not in original:
                raise KeyError(f"Key '{key}' not found in the original dictionary.")
            if isinstance(original[key], dict):
                update_dict(original[key], value)
            else:
                original[key] = value
        elif isinstance(value, list):
            if key not in original:
                raise KeyError(f"Key '{key}' not found in the original dictionary.")
            if isinstance(original[key], list):
                for i, item in enumerate(value):
                    if i < len(original[key]) and isinstance(item, dict):
                        update_dict(original[key][i], item)
                    else:
                        if i < len(original[key]):
                            original[key][i] = item
                        else:
                            original[key].append(item)
            else:
                original[key] = value
        else:
            if key not in original:
                raise KeyError(f"Key '{key}' not found in the original dictionary.")
            original[key] = value
    return original


def copy_with_changes(
        dictionary: Union[str, pathlib.Path, Dict[str, Any]],
        changes: Union[str, pathlib.Path, Dict[str, Any]],
        output: Optional[Union[str, pathlib.Path]] = None
) -> Optional[Dict[str, Any]]:
    """
    Changes dictionary fields according to changed dictionary. Optionally saves CHANGED dictionary.
    Inputs may be either yaml files or dictionaries.
    """

    # Determine if inputs are paths or dictionaries
    if isinstance(dictionary, (str, pathlib.Path)):
        original_dict = load_yaml(pathlib.Path(dictionary))
    else:
        original_dict = dictionary

    if isinstance(changes, (str, pathlib.Path)):
        changes_dict = load_yaml(pathlib.Path(changes))
    else:
        changes_dict = changes

    # Apply changes
    update_dict(original_dict, changes_dict)

    # Determine if the output is a path or needs to be returned
    if isinstance(output, (str, pathlib.Path)):
        save_yaml(original_dict, pathlib.Path(output))
    else:
        return original_dict


# Example usage of the function
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Apply changes to a dictionary YAML file.")
    parser.add_argument('--dictionary', type=pathlib.Path, required=True, help="Path to the original YAML file")
    parser.add_argument('--changes', type=pathlib.Path, required=True, help="Path to the changes YAML file")
    parser.add_argument('--output', type=pathlib.Path, required=True, help="Path to save the updated YAML file")
    args = parser.parse_args()

    copy_with_changes(args.dictionary, args.changes, args.output)
    print(f"Changes applied and saved to {args.output}")