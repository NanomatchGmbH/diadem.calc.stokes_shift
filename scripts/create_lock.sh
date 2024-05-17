docker run -it --rm -v $(pwd):/tmp -u $(id -u):$(id -g)  mambaorg/micromamba:latest \
   /bin/bash -c "micromamba create --yes --name new_env --file /tmp/env.yml && \
                 micromamba env export --name new_env --explicit > env.lock"
