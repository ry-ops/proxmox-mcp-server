# Proxmox MCP Server Dockerfile
FROM node:20-alpine

LABEL org.opencontainers.image.title="Proxmox MCP Server"
LABEL org.opencontainers.image.description="MCP server for Proxmox VE management"
LABEL org.opencontainers.image.source="https://github.com/ry-ops/proxmox-mcp-server"
LABEL org.opencontainers.image.vendor="ry-ops"

RUN apk add --no-cache ca-certificates curl

WORKDIR /app

COPY package*.json ./

RUN npm ci --only=production && npm cache clean --force

COPY . .

RUN addgroup -g 1001 -S proxmox && \
    adduser -S -u 1001 -G proxmox proxmox && \
    chown -R proxmox:proxmox /app

USER proxmox

ENV NODE_ENV=production
ENV MCP_SERVER_TYPE=proxmox

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))" || exit 1

CMD ["node", "index.js"]
