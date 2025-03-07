micromamba create --name lock conda-lock
micromamba run -n lock conda-lock -f env.yml -p linux-64
