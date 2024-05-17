FROM mambaorg/micromamba:1.3.1

# We copy over the lockfile and install:
COPY --chown=$MAMBA_USER:$MAMBA_USER env.lock /tmp/env.lock
RUN micromamba install --name base --yes --file /tmp/env.lock && \
    micromamba clean --all --yes

# We also copy over the prepared local opt folder:
COPY --chown=$MAMBA_USER:$MAMBA_USER ./opt/. /opt/
COPY --chown=$MAMBA_USER:$MAMBA_USER ./entrypoint.sh /opt/entrypoint.sh

ENV WIBU_OVERRIDE replace_with_the_actual_value

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "/opt/entrypoint.sh"]
