def modify_command(command, params):
    # Create a dictionary to hold the parameter replacements
    replacements = {}
    for key, value in params.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                if isinstance(subvalue, dict):
                    for subsubkey, subsubvalue in subvalue.items():
                        replacements[f"{key}.{subkey}.{subsubkey}"] = subsubvalue
                else:
                    replacements[f"{key}.{subkey}"] = subvalue
        else:
            replacements[key] = value

    # Replace the placeholders in the command
    for key, value in replacements.items():
        placeholder = f"${{{key}}}"
        command = command.replace(placeholder, str(value))

    return command

def test_modify_command():
    command = (
        "Deposit molecule.0.pdb=molecule_0.pdb molecule.0.spf=molecule_0.spf molecule.0.conc=1.0 "
        "simparams.Thi=4000.0 simparams.Tlo=300.0 simparams.sa.Tacc=5.0 simparams.sa.cycles=${UC_PROCESSORS_PER_NODE} "
        "simparams.sa.steps=${simparams.sa.steps} simparams.Nmol=${simparams.Nmol} simparams.moves.dihedralmoves=True "
        "Box.Lx=${Box.Lx} Box.Ly=${Box.Ly} Box.Lz=${Box.Lz} Box.pbc_cutoff=10.0 simparams.PBC=${simparams.PBC} "
        "machineparams.ncpu=${UC_PROCESSORS_PER_NODE} Box.grid_overhang=${Box.grid_overhang} "
        "simparams.postrelaxation_steps=${simparams.postrelaxation_steps}"
    )

    params = {
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
        },
        'UC_PROCESSORS_PER_NODE': 16
    }

    modified_command = modify_command(command, params)
    print("Modified Command:")
    print(modified_command)

if __name__ == "__main__":
    test_modify_command()
