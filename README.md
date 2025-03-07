 Diadem Image Template

This repository contains the minimal code required to create an image required to run a scientific diadem  workload via the Azure Batch service. The general workflow is: You provide a conda environment file, which is rendered to an explicit conda.lock (fixing all package versions and md5s), which is then used to build the docker image.
Extra scripts / binaries you require will be included in the diadem\_image\_template/opt folder automatically.

## Getting started
Use this repository as a template for your repository and rename it. Edit project\_config.sh to adapt the NAME according to your project, such as `xtb_example`. You will need docker installed and the docker daemon running to go through this tutorial. Therefore, install docker and start it (sudo systemctl enable docker, sudo systemctl start docker). Add yourself to the docker group (sudo gpasswd -a your\_user\_name docker). Reboot to make sure these changes took effect.

## Diadem Payload
### Input and output files
On the live server, your container will be executed in a working directory with the two input files

* molecule.yml, containing the smiles code
* calculator.yml, containing information about the calculation to be done

These files are directly taken from the Diadem databases outlined in the following image:
![](docs/images/tablestructure.png)

In production runs, on-demand computations will be executed using only these two files as input. Make sure your tool is designed accordingly. To develop your image, define the calculator(s) required for this run and save in calculators/your_calculator.yml, according to the definition of calculators provided in the diadem design document. 

```
calculator_id: your_calculator_id
provides:
- property_type_1_provided_by_calculator
- property_type_2_provided_by_calculator
- - ... 
specification:
  some_setting: some_value
```

For a DFT Payload specification could include Basis, Functional, convergence criteria, etc. It does not have to be a flat dictionary. The only requirement is that it is serializable into a list of dicts of dicts of lists... of python base types. Your payload then runs and your job must output a file called result.yml according to the following spec:

```
molecule_id:
  this_property_type:
    value: 5.0
    result:
      free_form_list: [ A, B, C ]
      free_form_dict: { A: B, C:D }
  this_other_property_tpye:
    value: 5.0
```
where molecule_id is the id of the input compound from the diadem database, this_(other_)property_type are the property-types defined in the provides field of the calculator, e.g. HOMO or LUMO in our example, and value has to be orderable (int, float, string, but not list of string). result is free form and includes additional data about this calculation. result is optional and can be omitted.

### Example: calculator and sample output of this XTB run
For our XTB example, we store the following lines in calculators/xtb_example.yml:

```
calculator_id: XTB_example
provides:
- HOMO
- LUMO
specification:
  numsteps: 200
```

The executable of this example (see below) correspondingly produces a file of the format:
```
molecule_id:
  HOMO:
    value: 5.0
  LUMO:
    value: 5.0
```

## Setting up the environment
Edit the diadem\_image\_template/env.yml file. This contains the specification of the conda environment, which will be rolled out inside the docker image. Only include direct dependencies in this file, i.e.: If you would include  matplotlib, which require the expat library, only include matplotlib. If you want a good env file for starting, you can prepare a conda environment with the tools you need and export it (see the following example). 

### Example: XTB and openbabel environment
We will now generate an environment containing XTB and openbabel. To start we installed Mambaforge for our architecture from here: https://github.com/conda-forge/miniforge . and set up an environment with the following script:

    mamba create --name=xtbdevenv xtb=6.6.0 openbabel python=3.11 pyyaml
    conda activate xtbdevenv
    mamba env export > env.yml
    cat env.yml

This outputs:
````{verbatim}
name: base  #<- keep or set this one to base.
channels:
  - conda-forge
dependencies:
  - _libgcc_mutex=0.1=conda_forge
  - _openmp_mutex=4.5=2_gnu
  - bzip2=1.0.8=h7f98852_4
  - ca-certificates=2022.12.7=ha878542_0
  - cairo=1.16.0=ha61ee94_1014
  - dftd4=3.5.0=h03160e7_0
  - expat=2.5.0=h27087fc_0
  - font-ttf-dejavu-sans-mono=2.37=hab24e00_0
  - font-ttf-inconsolata=3.000=h77eed37_0
  - font-ttf-source-code-pro=2.038=h77eed37_0
  - font-ttf-ubuntu=0.83=hab24e00_0
  - fontconfig=2.14.2=h14ed4e7_0
  - fonts-conda-ecosystem=1=0
  - fonts-conda-forge=1=0
  - ncurses=6.3=h27087fc_1
  - openbabel=3.1.1=py311h7c3e0e0_5
  - openssl=3.0.8=h0b41bf4_0
  - pcre2=10.40=hc3806b6_0
  - pip=23.0.1=pyhd8ed1ab_0
  - pixman=0.40.0=h36c2ea0_0
  - pthread-stubs=0.4=h36c2ea0_1001
  - python=3.11.0=he550d4f_1_cpython
  - xorg-xextproto=7.3.0=h7f98852_1002
  - stuff_ommited_here
  - xorg-xproto=7.0.31=h7f98852_1007
  - xtb=6.6.0=h03160e7_0
  - xz=5.2.6=h166bdaf_0
  - zlib=1.2.13=h166bdaf_4
prefix: /home/strunk/mambaforge/envs/xtbdevenv
````
We will edit this file to only include dependencies, we require directly and packages we care about, such as packages our own scripts requires (e.g. the python version).


````{verbatim}
name: base
channels:
  - conda-forge
dependencies:
  - openbabel=3.1.1
  - python=3.11.*
  - xtb=6.6.0
  - pyyaml=6.0.* <- always include yaml, you need it to parse the input files.
````
We will edit this file to only include dependencies, we require directly and packages we care about, such as packages our own scripts requires (e.g. the python version). Note that we whitelisted all newer python point releases and also removed the build string (such as h031607). This will be fixed in the next stage. When you are happy with your environment file, move it to the diadem\_image\_template subfolder and commit it to the repository. 


## Entrypoint for the payload
Your main entrypoint to execute your code is the file entrypoint.sh in the diadem\_image\_template subdirectory. Modify this file such that your code to read the input files and create a results.yml as specified above is executed by this entrypoint. 
If you require extra scripts or binaries put them in the diadem\_image\_template/opt subfolder. Remember to consider that you have to include the dependencies for your binaries in the conda env file. You can also generate an additional workdir\_bundle.tar.gz file, which will be staged out together with the actual results. This is meant for debugging purposes, so keep it small.


### Example: Executable for running xtb with molecule.yml and calculator.yml as input
In our example, we will change the entrypoint in the following way:
````{verbatim}
#!/bin/bash

# This file will start automatically in your docker run. You can assume the presence of a
# molecule.yml and a calculator.yml in the work directory.

# Make sure that after this script finishes a result.yml exists.
# The workdir_bundle.tar.gz will also be staged out for debugging purposes, if you create it.

python /opt/get_xtb_homo.py

# A good way to pack all files smaller than e.g 500k for stageout is:
find . -type f -size -500k -print0 | xargs -0 tar czf workdir_bundle.tar.gz
````

We are also going to add diadem\_image\_template/opt/get\_xtb\_homo.py with the following content:
````{verbatim}

#!/usr/bin/env python3
import yaml
import subprocess
import shlex

with open("molecule.yml",'rt') as infile:
    moldict = yaml.safe_load(infile)

with open("calculator.yml",'rt') as infile:
    calcdict = yaml.safe_load(infile)

# The engine, which was instantiated needs to provide "provides" (e.g HOMO and LUMO)
provides = calcdict["provides"]

# This is a free form dictionary. For the example, we just provide numsteps
steps = calcdict["specification"]["numsteps"]

#we read smiles and molid
smiles = moldict["smiles"]
molid = moldict["id"]

# we generate a bad 3d structure
command = f"obabel -:{smiles} -o xyz -O mol.xyz --gen3d"
subprocess.check_output(shlex.split(command))

# we optimize the bad 3d structure
command = "xtb mol.xyz --opt"
output = subprocess.check_output(shlex.split(command), encoding="utf8", text=True).split("\n")

# we calculate homo and lumo
command = "xtb xtbopt.xyz"
output = subprocess.check_output(shlex.split(command), encoding="utf8", text=True).split("\n")

with open("out.log",'wt') as outfile:
    outfile.write("\n".join(output))

resultdict =  { molid: {} }

for line in output:
    for tag in provides:
        if f"({tag})" in line: # xtb logs homo lumo out as (HOMO) and (LUMO)
            splitline = line.split()
            value = float(splitline[-2])
            resultdict[molid][tag] = value

with open("result.yml",'wt') as outfile:
    yaml.dump(resultdict, outfile)

````

## Locking the environment
Inside the diadem\_image\_template folder: The env file is the file specifying, what you need. For operational stability, we will now lock down, how the package manager fulfilled this request and record it. Call the script `../scripts/create_lock.sh`. Docker will now build a temporary image, install the environment and output an env.lock file. Commit it to the repository.

### Push a git tag
To allow for automatic versioning of the image, add a tag, like this:

```
    git tag -a "name_as_in_project_config.sh/v0.0.1" -m "First version definition"
    git push origin "name_as_in_project_config.sh/v0.0.1"
```

This will alllow automatic tagging of generated images. Everytime you want to not only build an image (for example for testing) but also upload it (for deployment on the diadem infrastructure), you need to set an explicit tag with a version higher than the last one and push it like above. If you want to know the current version, just use `git describe` (after the first tag).

### Building the image
Inside the diadem\_image\_template folder: Make sure there is nothing uncommited in the repository and call `../scripts/build_image.sh`. The image will be tagged with the output of git describe (i.e. the most current tag modified).

### Testing the image
The image should now contain all dependencies required to execute your scientific software. If you run pytest, the image will be tested with all combinations of Calculators defined in `Calculators/*.yml` and `Molecules` defined in tests/inputs/molecules`. For every test done, a folder tests/calculator/molecule will be generated. If the test was successful, the generated result.yml will be put into this folder. Check it and add it to the repository, the next time a test is run, the two dictionaries will be compared and an error generated if they differ.
