FROM mambaorg/micromamba:latest

# We copy over the lockfile and install:
COPY --chown=$MAMBA_USER:$MAMBA_USER conda-lock.yml /tmp/conda-lock.yml
RUN micromamba install --name base --yes --file /tmp/conda-lock.yml && \
    micromamba clean --all --yes

# We also copy over the prepared local opt folder:
COPY --chown=$MAMBA_USER:$MAMBA_USER ./opt/. /opt/
COPY --chown=$MAMBA_USER:$MAMBA_USER ./entrypoint.sh /opt/entrypoint.sh

ENV WIBU_OVERRIDE replace_with_the_actual_value

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "/opt/entrypoint.sh"]
