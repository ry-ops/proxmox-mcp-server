<img src="https://github.com/ry-ops/proxmox-mcp-server/blob/main/proxmox-mcp-server.png" width="100%">

# Proxmox MCP Server

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-latest-green.svg)](https://github.com/astral-sh/uv)
[![MCP](https://img.shields.io/badge/MCP-1.0-purple.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A Model Context Protocol (MCP) server for interacting with Proxmox Virtual Environment API. This server provides comprehensive tools for managing VMs, containers, storage, and cluster resources through the MCP interface.

**Built with Python and `uv` for fast, reliable dependency management.**

## Features

### Virtual Machine Management
- List all VMs (node-specific or cluster-wide)
- Get VM configuration and status
- Start, stop, shutdown, and reboot VMs
- Create, list, and delete VM snapshots

### Container Management
- List LXC containers
- Get container status
- Start and stop containers

### Node & Cluster Management
- List all cluster nodes
- Get node status and resource usage
- Get overall cluster status

### Storage Management
- List storage devices
- Get storage status and usage

### Task Management
- List running and recent tasks
- Get task status and progress

## Quick Start

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Run setup script
chmod +x setup.sh
./setup.sh

# 3. Set environment variables
export PROXMOX_HOST="192.168.1.100"
export PROXMOX_USER="root@pam"
export PROXMOX_TOKEN_NAME="automation"
export PROXMOX_TOKEN_VALUE="your-token-here"

# 4. Test connection
./test-connection.sh

# 5. Configure Claude Desktop and restart
```

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## Installation

### Prerequisites

- Python 3.10 or higher
- `uv` package manager
- Proxmox VE 6.0 or later

### Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone or download this repository
cd proxmox-mcp-server

# Run setup script (creates structure and installs dependencies)
./setup.sh

# Or manually:
mkdir -p src/proxmox_mcp_server
# Place server.py and __init__.py in src/proxmox_mcp_server/
uv sync
```

## Configuration

The server is configured via environment variables:

### Required Variables

- `PROXMOX_HOST`: Proxmox server hostname or IP address
- `PROXMOX_USER`: Username (e.g., `root@pam`, `admin@pve`)

### Authentication (choose one method)

**Option 1: API Token (Recommended)**
- `PROXMOX_TOKEN_NAME`: API token name
- `PROXMOX_TOKEN_VALUE`: API token value

**Option 2: Password**
- `PROXMOX_PASSWORD`: User password

### Optional Variables

- `PROXMOX_PORT`: API port (default: `8006`)
- `PROXMOX_VERIFY_SSL`: Verify SSL certificates (default: `false`)

## Setting Up Proxmox Authentication

### Creating an API Token (Recommended)

1. Log into your Proxmox web interface
2. Navigate to **Datacenter** → **Permissions** → **API Tokens**
3. Click **Add** and create a token for your user
4. Uncheck "Privilege Separation" to inherit user permissions
5. Copy the Token ID and Secret (you won't see it again!)

Example token format:
```bash
PROXMOX_TOKEN_NAME=automation
PROXMOX_TOKEN_VALUE=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

The full token identifier will be: `root@pam!automation`

### Using Password Authentication

Simply set your user password:
```bash
export PROXMOX_PASSWORD=yourpassword
```

## MCP Configuration

Add to your Claude Desktop configuration file:

**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

### With API Token (Recommended)

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/proxmox-mcp-server",
        "run",
        "proxmox-mcp-server"
      ],
      "env": {
        "PROXMOX_HOST": "192.168.1.100",
        "PROXMOX_USER": "root@pam",
        "PROXMOX_TOKEN_NAME": "automation",
        "PROXMOX_TOKEN_VALUE": "your-token-value-here"
      }
    }
  }
}
```

### With Password

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/proxmox-mcp-server",
        "run",
        "proxmox-mcp-server"
      ],
      "env": {
        "PROXMOX_HOST": "192.168.1.100",
        "PROXMOX_USER": "root@pam",
        "PROXMOX_PASSWORD": "your-password-here"
      }
    }
  }
}
```

**Important**: Use the absolute path to your project directory!

## Available Tools

### Node Management

- **list_nodes**: List all nodes in the cluster
- **get_node_status**: Get status and resource usage for a specific node

### Virtual Machine Tools

- **list_vms**: List all VMs (optionally filtered by node)
- **get_vm_config**: Get VM configuration
- **get_vm_status**: Get current VM status
- **start_vm**: Start a VM
- **stop_vm**: Force stop a VM
- **shutdown_vm**: Gracefully shutdown a VM
- **reboot_vm**: Reboot a VM
- **create_vm_snapshot**: Create a VM snapshot
- **list_vm_snapshots**: List all VM snapshots
- **delete_vm_snapshot**: Delete a VM snapshot

### Container Tools

- **list_containers**: List all LXC containers on a node
- **get_container_status**: Get container status
- **start_container**: Start a container
- **stop_container**: Stop a container

### Storage Tools

- **list_storage**: List all storage devices
- **get_storage_status**: Get storage status and usage

### Task Tools

- **list_tasks**: List running and recent tasks
- **get_task_status**: Get status of a specific task

### Cluster Tools

- **get_cluster_status**: Get overall cluster status and resources

## Example Usage

Once configured, you can ask Claude to interact with your Proxmox environment:

> "Can you list all VMs in my Proxmox cluster?"

> "What's the status of VM 100 on node pve1?"

> "Start VM 105 on node pve1"

> "Create a snapshot called 'backup-2025' for VM 100 on pve1"

> "Show me the storage usage on all nodes"

> "List all running tasks in the cluster"

## Development

```bash
# Install dependencies
uv sync

# Run the server directly
uv run proxmox-mcp-server

# Run with custom environment
PROXMOX_HOST=192.168.1.100 \
PROXMOX_USER=root@pam \
PROXMOX_TOKEN_NAME=automation \
PROXMOX_TOKEN_VALUE=your-token \
uv run proxmox-mcp-server

# Install development dependencies
uv sync --all-extras

# Run tests (if implemented)
uv run pytest
```

## Project Structure

```
proxmox-mcp-server/
├── src/
│   └── proxmox_mcp_server/
│       ├── __init__.py       # Package initialization
│       └── server.py         # Main server implementation
├── pyproject.toml            # Project configuration
├── uv.lock                   # Locked dependencies (generated)
├── .env.example              # Environment variable template
├── .gitignore                # Git ignore patterns
├── setup.sh                  # Automated setup script
├── test-connection.sh        # Connection test script
├── README.md                 # This file
├── QUICKSTART.md            # 5-minute setup guide
├── SETUP.md                  # Detailed setup guide
└── USAGE.md                  # Usage examples

```

## Security Considerations

- **API Tokens** are more secure than password authentication as they can be revoked independently
- Set `PROXMOX_VERIFY_SSL=true` in production environments with valid SSL certificates
- Grant minimal required permissions to API tokens
- Store credentials securely and never commit them to version control
- Consider network restrictions (firewall rules) for API access

## Troubleshooting

### Authentication Errors

- Verify your credentials are correct
- Check that the user has appropriate permissions
- For API tokens, ensure the token hasn't expired or been revoked
- Ensure "Privilege Separation" was unchecked when creating the token

### Connection Errors

- Verify `PROXMOX_HOST` and `PROXMOX_PORT` are correct
- Check network connectivity to the Proxmox host
- If using SSL verification, ensure certificates are valid
- Test with: `curl -k https://YOUR_HOST:8006/api2/json/version`

### Permission Errors

- The user/token needs appropriate privileges for the operations
- Common required privileges: `VM.Monitor`, `VM.Audit`, `Datastore.Audit`, `Sys.Audit`, `VM.PowerMgmt`, `VM.Snapshot`

### Debug Mode

To see detailed logs, check stderr output when running the server. The server logs authentication method and connection status to stderr (visible in Claude Desktop logs).

### Tools Not Showing in Claude

- Verify the path in Claude config is absolute, not relative
- Check that the config file is valid JSON
- Ensure you completely quit and restarted Claude Desktop (not just closed the window)
- Check Claude Desktop logs for errors

## Testing Connection

Before configuring Claude, test your Proxmox connection:

```bash
# Set environment variables
export PROXMOX_HOST="192.168.1.100"
export PROXMOX_USER="root@pam"
export PROXMOX_TOKEN_NAME="automation"
export PROXMOX_TOKEN_VALUE="your-token-here"

# Run test script
./test-connection.sh
```

The script will verify:
1. Connection to Proxmox
2. API availability
3. Authentication
4. Permission to list nodes
5. Access to cluster resources

## API Documentation

For more information about the Proxmox VE API:
- [Proxmox VE API Documentation](https://pve.proxmox.com/wiki/Proxmox_VE_API)
- [API Viewer](https://pve.proxmox.com/pve-docs/api-viewer/)
- [Proxmox VE Administration Guide](https://pve.proxmox.com/pve-docs/pve-admin-guide.html)

## Dependencies

- **mcp** (>=1.0.0): Model Context Protocol SDK
- **httpx** (>=0.27.0): Modern HTTP client for Python

## Roadmap

Future enhancements may include:

- VM creation and deletion
- Container creation and deletion
- Backup management
- Network configuration
- User and permission management
- Resource pool management
- HA (High Availability) management
- Firewall rule management
- Certificate management
- Real-time monitoring and alerts

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

Areas for improvement:
- Additional tools/features
- Better error handling
- Performance optimizations
- Documentation improvements
- Test coverage
- Bug fixes

## License

MIT

## Related Projects

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Proxmox VE](https://www.proxmox.com/en/proxmox-virtual-environment)
- [uv - Python Package Manager](https://github.com/astral-sh/uv)
- [MCP Servers Collection](https://github.com/modelcontextprotocol/servers)

## Support

If you encounter issues:

1. Check the documentation files:
   - [QUICKSTART.md](QUICKSTART.md) - Quick setup
   - [SETUP.md](SETUP.md) - Detailed setup with security
   - [USAGE.md](USAGE.md) - Usage examples

2. Test your connection with `./test-connection.sh`

3. Check Claude Desktop logs for errors

4. Verify Proxmox server logs: `/var/log/pve/`

5. Review Proxmox API documentation

## Acknowledgments

This project uses:
- The Model Context Protocol by Anthropic
- Proxmox VE API
- Python httpx for HTTP requests
- uv for fast Python package management

---

**Ready to get started?** → See [QUICKSTART.md](QUICKSTART.md)

**Need detailed setup?** → See [SETUP.md](SETUP.md)

**Want examples?** → Check [USAGE.md](USAGE.md)
