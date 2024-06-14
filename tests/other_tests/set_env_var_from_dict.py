import os


def set_env_variables_from_dict(env_vars):
    def set_env(prefix, d):
        for key, value in d.items():
            if isinstance(value, dict):
                set_env(f"{prefix}.{key}", value)
            else:
                os.environ[f"{prefix}.{key}"] = str(value)

    for key, value in env_vars.items():
        set_env(key, value)

    return dict(os.environ)


env_vars = {
    "simparams": {
        "Nmol": 1000,
        "PBC": True,
        "sa": {
            "steps": 130000
        },
        "postrelaxation_steps": 10000
    },
    "Box": {
        "Lx": 40.0,
        "Ly": 40.0,
        "Lz": 120.0,
        "grid_overhang": 20
    }
}

updated_env = set_env_variables_from_dict(env_vars)
print(updated_env)
