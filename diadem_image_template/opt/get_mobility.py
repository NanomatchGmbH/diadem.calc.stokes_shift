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
inchi = moldict["inchi"]
inchiKey = moldict["inchiKey"]

# we generate a bad 3d structure
with open("mol.inchi",'w') as outfile:
    outfile.write(f"{inchi}\n")

command = f"obabel -i inchi mol.inchi -o xyz -O mol.xyz --gen3d"
subprocess.check_output(shlex.split(command))

# we optimize the bad 3d structure
command = "xtb mol.xyz --opt"
output = subprocess.check_output(shlex.split(command), encoding="utf8", text=True).split("\n")



###### -->
# we calculate homo and lumo
#command = "xtb xtbopt.xyz"
#output = subprocess.check_output(shlex.split(command), encoding="utf8", text=True).split("\n")

#with open("out.log",'wt') as outfile:
#    outfile.write("\n".join(output))
###### <--

resultdict =  { inchiKey: {} }  # dummy output

###### -->
#for line in output:
#    for tag in provides:
#        if f"({tag})" in line: # xtb logs homo lumo out as (HOMO) and (LUMO)
#            splitline = line.split()
#            value = float(splitline[-2])
#            resultdict[inchiKey][tag] = value
###### <--


#!--> dummy output
for tag in provides:
    resultdict[inchiKey][tag] = 0
#!<--

with open("result.yml",'wt') as outfile:
    yaml.dump(resultdict, outfile)
