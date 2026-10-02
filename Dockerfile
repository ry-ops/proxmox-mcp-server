# Proxmox MCP Server Dockerfile
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Proxmox MCP Server"
LABEL org.opencontainers.image.description="MCP server for Proxmox VE management"
LABEL org.opencontainers.image.source="https://github.com/ry-ops/proxmox-mcp-server"
LABEL org.opencontainers.image.vendor="ry-ops"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# Install with the http extra so streamable-HTTP transport is available.
RUN pip install --no-cache-dir ".[http]"

RUN groupadd -g 1001 proxmox && \
    useradd -u 1001 -g proxmox -s /bin/sh proxmox && \
    chown -R proxmox:proxmox /app

USER proxmox

# Default to HTTP transport for remote (v-assist) deployments.
ENV MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8080

EXPOSE 8080

CMD ["proxmox-mcp-server"]
