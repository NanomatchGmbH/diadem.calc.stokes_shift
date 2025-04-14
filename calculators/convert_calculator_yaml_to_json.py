import yaml
import json
import sys

def convert_yaml_to_json(yaml_path, json_path):
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    # Wrap it into a dictionary with numeric keys for compatibility
    out = {
        "0": {
            "calculatorId": data["calculatorId"],
            "version": data["version"],
            "specification": data["specification"],
            "provides": data["provides"],
            "files": data.get("files", []),
            "price": data.get("price", 0),
            "onDemandEnabled": data.get("onDemandEnabled", False)
        }
    }

    # Optional on-demand fields
    if data.get("onDemandEnabled", False):
        out["0"]["poolId"] = data.get("poolId")
        out["0"]["image"] = data.get("image")
        out["0"]["operationFiles"] = data.get("operationFiles", {})

    with open(json_path, 'w') as f:
        json.dump(out, f, indent=2)

    print(f"✅ Converted YAML to JSON: {json_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert_calculator_yaml_to_json.py input.yaml output.json")
    else:
        convert_yaml_to_json(sys.argv[1], sys.argv[2])
