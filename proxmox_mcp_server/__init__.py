"""
Proxmox MCP Server
==================

A Model Context Protocol (MCP) server for managing Proxmox Virtual Environment.

This package provides comprehensive tools for interacting with Proxmox VE through
Claude AI, enabling natural language management of virtual machines, containers,
storage, and cluster resources.

Features:
---------
- VM management (start, stop, shutdown, reboot, status, configuration)
- Container operations (list, start, stop, status)
- Snapshot management (create, list, delete)
- Storage monitoring and status
- Task tracking and progress monitoring
- Cluster resource overview
- Node status and resource usage
- API token and password authentication support

Requirements:
-------------
- Python 3.10+
- Proxmox VE 6.0+
- Valid API token or password authentication

Usage:
------
Configure via environment variables:
    - PROXMOX_HOST: Proxmox server hostname/IP (required)
    - PROXMOX_USER: Username with realm (required)
    - PROXMOX_TOKEN_NAME: API token name (recommended)
    - PROXMOX_TOKEN_VALUE: API token value (recommended)
    - PROXMOX_PASSWORD: Password (alternative to token)
    - PROXMOX_PORT: API port (default: 8006)
    - PROXMOX_VERIFY_SSL: Verify SSL certificates (default: false)

Example:
    export PROXMOX_HOST="192.168.1.100"
    export PROXMOX_USER="root@pam"
    export PROXMOX_TOKEN_NAME="automation"
    export PROXMOX_TOKEN_VALUE="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    
    uv run proxmox-mcp-server

Links:
------
- GitHub: https://github.com/ry-ops/proxmox-mcp-server
- Documentation: https://github.com/ry-ops/proxmox-mcp-server#readme
- MCP Protocol: https://modelcontextprotocol.io/
- Proxmox API: https://pve.proxmox.com/pve-docs/api-viewer/

License:
--------
MIT License - see LICENSE file for details

Author:
-------
ry-ops

"""

__version__ = "1.0.0"
__author__ = "ry-ops"
__license__ = "MIT"
__url__ = "https://github.com/ry-ops/proxmox-mcp-server"

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "__url__",
]
