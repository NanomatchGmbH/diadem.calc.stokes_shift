#!/bin/bash

# This file will start automatically in your docker run. You can assume the presence of a 
# molecule.yml and a calculator.yml in the work directory.

# Get the number of CPUs (if needed, replace this logic with your actual CPU detection script)
ncpus=120

export OMP_NUM_THREADS=${ncpus}
export UC_PROCESSORS_PER_NODE=${ncpus}
export NM_LICENSE_SERVER=123.123.123.123

python /opt/get_mobility.py

# Make sure that after this script finishes a result.yml exists.
# The workdir_bundle.tar.gz will also be staged out for debugging purposes, if you create it. 

# A good way to pack all files smaller than e.g 500k for stageout is:
find . -type f -print0 | xargs -0 tar czf workdir_bundle.tar.gz
