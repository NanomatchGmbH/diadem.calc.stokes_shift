#!/bin/bash

WORKING_DIR=`pwd`
DATA_DIR=$WORKING_DIR

# Use a writable directory
if [ -d "$SCRATCH" ]; then
    WORKING_DIR="$SCRATCH/$(whoami)/$GENERATED_UUID"
elif [ -d "$HOME" ]; then
    WORKING_DIR="$HOME/tmp/$GENERATED_UUID"
else
    echo "No suitable directory found for WORKING_DIR"
    exit 1
fi

mkdir -p $WORKING_DIR
cp -r $DATA_DIR/* $WORKING_DIR/



echo "Deposit running on node $(hostname) in directory $WORKING_DIR"
cd $WORKING_DIR

export DO_RESTART="False"
if [ "$DO_RESTART" == "True" ]
then
    if [ -f restartfile.zip ]
    then
        zip -qT restartfile.zip
        if [ "$?" != "0" ]
        then
            echo "Could not read restartfile. Aborting run."
            exit $?
        fi
        echo "Found Checkpoint, extracting for restart."
        unzip -q -o restartfile.zip
        rm restartfile.zip
    else
        echo "Restart was enabled, but no checkpoint file was found. Not starting simulation."
        exit 5
    fi
fi


Deposit  molecule.0.pdb=molecule_0.pdb  molecule.0.spf=molecule_0.spf molecule.0.conc=1.0   simparams.Thi=4000.0  simparams.Tlo=300.0 simparams.sa.Tacc=5.0 simparams.sa.cycles=${UC_PROCESSORS_PER_NODE} simparams.sa.steps=130000 simparams.Nmol=1000 simparams.moves.dihedralmoves=True  Box.Lx=50.0  Box.Ly=50.0  Box.Lz=180.0  Box.pbc_cutoff=20.0  simparams.PBC=True machineparams.ncpu=${UC_PROCESSORS_PER_NODE} Box.grid_overhang=30 simparams.postrelaxation_steps=10000


obabel structure.cml -O structure.mol2

if [ "True" == "True" ]
then
    $DEPTOOLS/add_periodic_copies.py 7.0
    mv periodic_output/structurePBC.cml .
    rm -f periodic_output/*.cml
    zip -r periodic_output_single_molecules.zip periodic_output
    rm -r periodic_output/
fi


zip restartfile.zip deposited_*.pdb.gz static_parameters.dpcf.gz static_parameters.dpcf_molinfo.dat.gz grid.vdw.gz grid.es.gz neighbourgrid.vdw.gz

rm deposited_*.pdb.gz deposited_*.cml static_parameters.dpcf.gz grid.vdw.gz grid.es.gz neighbourgrid.vdw.gz

if [ -d $SCRATCH ] || [ -d $HOME ]; then
    if [ -d $WORKING_DIR ]; then
        mkdir -p $DATA_DIR
        cp -r $WORKING_DIR/* $DATA_DIR/
        find $DATA_DIR -type f \( -name "*.stderr" -o -name "*.stdout" -o -name "stdout" -o -name "stderr" \) -exec rm -f {} +
        cd $DATA_DIR
        rm -r $WORKING_DIR
    fi
fi


QuantumPatchAnalysis > DensityAnalysisInit.out
QuantumPatchAnalysis Analysis.Density.enabled=True Analysis.RDF.enabled=True #> DensityAnalysis.out

cat deposit_settings.yml >> output_dict.yml
