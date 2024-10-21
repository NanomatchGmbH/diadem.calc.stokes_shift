# This folder
## Contents

Every folder contains calculators deployed to the diadem.

## Purpose

If you want to deploy something to diadem:
1. Hand-craft the calculator yaml files and put to the folder `./yaml`.
2. Use `merge_yaml_convert_to_json.py` script to convert all calculators from `./yaml` to `./json`. There will be a single `json` file.
3. use userscript to add calculator and get its `id`.

## How to convert yaml files to a json file:
```commandline
python yaml_to_json.py 120_2.0.1
```

## Name convention

Name nested folders descriptively. Suggestion: `<num_cpu>_<version>`, with `<num_cpu>` being the number of _physicsl_ CPUs and the `<version>` is the image version.
Example: `120_2.0.1`.

# Nested folders

This is about the content of every nested folder in this folder.

## Contents
Calculators in two formats:
- `./yaml`: hand-crafted yaml files of the calculators.
- `./json`: automatically generated based on the content of the `./yaml` folder. 
- `convert_to_yaml.py`: converts all calculators created in yaml to one json file to use with `add_calculators.sh` userscript.
- `update_dict.py`: will take raw outputs from `/txt` folder and produce folder `<name_of_folder>/json/update_dict`
Content of this folder is the json file comprising Calculator tables based on the content of the `yaml`  folder.
 
## Note 

When designing yaml calculators files:
1. `id` field does not exist.
2. Calculator version, key `version` is what the user see, must correspond the field image version, `diadem.azurecr.io/<image_name>:<image_version>`

# Workflow

1. Create calculators yaml in `/yaml`
2. Generate json calculators from separate yaml files in `yaml`.
3. Add calculators to diadem using userscripts.
4. Generate output for `.txt` folder using userscript, see `/txt.README.md`
5. Run `update_dict.py` to generate the `/json/update_dicts/*.json`.
6. Add `id` to the calculators using userscripts.