# Streamable-HTTP Transport

This fork adds a second entrypoint, `proxmox_mcp/server_http.py`, alongside
upstream's stdio-only `proxmox_mcp/server.py`. It reuses the exact same tool
registry and `ProxmoxClient` — only the transport differs — so it stays in
sync with upstream's tool additions/fixes with no extra work.

## Running it

```bash
uv sync
PROXMOX_HOST=... PROXMOX_USER=... PROXMOX_TOKEN_NAME=... PROXMOX_TOKEN_VALUE=... \
  uv run proxmox-mcp-server-http
```

The server listens on `MCP_HTTP_HOST`:`MCP_HTTP_PORT` (default `0.0.0.0:8811`)
and serves streamable-HTTP MCP at the `/mcp` path (note the trailing slash —
`/mcp/`, or a client following the redirect).

## Why a separate file instead of changing `server.py`

`mcp` 2.0 replaced the `@app.list_tools()` / `@app.call_tool()` decorator API
(what upstream's `server.py` uses) with a constructor-callback style. Rather
than rewrite upstream's tool-registration code, this fork pins
`mcp>=1.9.0,<2.0.0` and adds the HTTP transport using that same version's
`StreamableHTTPSessionManager` directly (the manual wiring pattern the SDK
itself uses before its newer `Server.streamable_http_app()` convenience
method existed). `server.py` is otherwise unmodified from upstream.

## Verified

Manually smoke-tested end-to-end against a dummy Proxmox target: server
boots, authenticates via API token, accepts a real MCP `initialize` request
over HTTP, and returns the full tool catalog via `tools/list`. Not yet
exercised against a real Proxmox cluster.
