#!/bin/bash

# This file will start automatically in your docker run. You can assume the presence of a 
# molecule.yml and a calculator.yml in the work directory.

# Get the number of CPUs (if needed, replace this logic with your actual CPU detection script)
ncpus=120
ALLOW_BUNDLE=true  # Set this to false to prevent bundle creation. False will save some time in production.

export OMP_NUM_THREADS=${ncpus}
export UC_PROCESSORS_PER_NODE=${ncpus}
export NM_LICENSE_SERVER=123.123.123.123

python /opt/get_mobility.py

if [ "$ALLOW_BUNDLE" = true ]; then
    # If bundling is allowed, bundle all files smaller than 500k
    find . -type f -size -500k -print0 | xargs -0 tar czf workdir_bundle.tar.gz
else
    # If bundling is not allowed, only bundle README and log.txt and explains why
    if [ -f log.txt ]; then
        echo "log.txt exists." > README
        echo "This archive INTENTIONALLY contains log.txt only, no other files from the working directory. Intentionally." >> README
        tar czf workdir_bundle.tar.gz README log.txt
    else
        echo "log.txt was not found. Something went wrong." > README
        echo "This archive contains only the README file, as log.txt was missing. No other files from the working directory were supposed to be included. Intentionally." >> README
        tar czf workdir_bundle.tar.gz README
    fi
fi