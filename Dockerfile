ARG TAMTREE_VERSION=0.1.0
FROM ghcr.io/tamtree/tamtree:${TAMTREE_VERSION}

USER root
# The image's Python environment has no pip, so bring uv in to install.
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv
COPY . /src/tamtree-linkedin-connector
RUN uv pip install --python /app/.venv/bin/python --no-cache /src/tamtree-linkedin-connector \
 && rm -rf /src /usr/local/bin/uv
USER tamtree
