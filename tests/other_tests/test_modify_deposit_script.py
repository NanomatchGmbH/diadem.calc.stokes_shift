from diadem_image_template.opt.utils.modify_deposit_script import copy_deposit_init_with_changes


def test_modify_deposit_script(tmp_path):
    # Create a temporary source script
    source_script = tmp_path / 'deposit_init.sh'
    output_script = tmp_path / 'modified_deposit_init.sh'

    initial_script_content = """
#!/bin/bash
Deposit molecule.0.pdb=molecule_0.pdb molecule.0.spf=molecule_0.spf molecule.0.conc=1.0 simparams.Thi=4000.0 simparams.Tlo=300.0 simparams.sa.Tacc=5.0 simparams.sa.cycles=10 simparams.sa.steps=13000 simparams.Nmol=10 simparams.moves.dihedralmoves=True Box.Lx=25.0 Box.Ly=25.0 Box.Lz=90.0 Box.pbc_cutoff=25.0 simparams.PBC=True machineparams.ncpu=8 Box.grid_overhang=30 simparams.postrelaxation_steps=1000
"""
    with open(source_script, 'w') as file:
        file.write(initial_script_content)

    # Define the parameters to modify
    changes = {
        'simparams': {
            'Nmol': 100,
            'PBC': True,
            'sa': {
                'steps': 130000,
                'cycles': 30
            },
            'postrelaxation_steps': 10000
        },
        'Box': {
            'Lx': 40.0,
            'Ly': 40.0,
            'Lz': 120.0,
            'grid_overhang': 20
        }
    }

    # Modify the script
    copy_deposit_init_with_changes(source_script, changes, output_script)

    # Read the modified script
    with open(output_script, 'r') as file:
        modified_content = file.read()

    # Expected deposit line
    expected_deposit_line = "Deposit molecule.0.pdb=molecule_0.pdb molecule.0.spf=molecule_0.spf molecule.0.conc=1.0 simparams.Thi=4000.0 simparams.Tlo=300.0 simparams.sa.Tacc=5.0 simparams.sa.cycles=30 simparams.sa.steps=130000 simparams.Nmol=100 simparams.moves.dihedralmoves=True Box.Lx=40.0 Box.Ly=40.0 Box.Lz=120.0 Box.pbc_cutoff=25.0 simparams.PBC=True machineparams.ncpu=8 Box.grid_overhang=20 simparams.postrelaxation_steps=10000\n"

    assert expected_deposit_line in modified_content, "The modified script content does not match the expected content."
