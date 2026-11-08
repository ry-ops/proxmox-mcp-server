# Proxmox MCP Server Dockerfile
# Base images are pinned by digest; Dependabot (docker) keeps them current.

# --- build: install the exact versions in uv.lock into /opt/venv ---
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS build

COPY --from=ghcr.io/astral-sh/uv:0.12.10@sha256:2bb3ebca0a796a155094a27773d290c4b074572e6107f171d88d086682fd2500 /uv /bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY proxmox_mcp ./proxmox_mcp

# --locked fails the build if uv.lock is out of date with pyproject.toml.
RUN uv sync --locked --no-dev --no-editable

# --- runtime ---
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

LABEL org.opencontainers.image.title="Proxmox MCP Server"
LABEL org.opencontainers.image.description="MCP server for Proxmox VE management"
LABEL org.opencontainers.image.source="https://github.com/ry-ops/proxmox-mcp-server"
LABEL org.opencontainers.image.vendor="ry-ops"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1001 proxmox && \
    useradd -u 1001 -g proxmox -s /bin/sh proxmox

COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
USER proxmox

ENV MCP_SERVER_TYPE=proxmox

CMD ["proxmox-mcp-server"]
