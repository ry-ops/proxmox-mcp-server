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

### Agent-to-Agent (A2A) Protocol Support

This server implements the **A2A protocol** for seamless agent-to-agent communication. The included `agent-card.json` file provides:

- **Structured agent capabilities** - Detailed skill definitions for AI-to-AI discovery
- **Authentication specifications** - Clear auth requirements for automated integration
- **Tool catalog** - Complete inventory of available operations organized by category
- **MCP protocol support** - Native Model Context Protocol implementation

**Use Cases:**
- Multi-agent orchestration systems
- Automated infrastructure workflows
- Agent discovery and composition
- Cross-system AI collaboration

See the [A2A Protocol Documentation](#a2a-protocol) section below for integration details.

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

## A2A Protocol

### Overview

This Proxmox MCP server implements the **Agent-to-Agent (A2A) protocol**, enabling AI agents to discover, communicate with, and orchestrate infrastructure management tasks autonomously.

### Agent Card

The `agent-card.json` file serves as the agent's identity and capability manifest. It provides:

**Location:** `/agent-card.json` (repository root)

**Contents:**
- Agent name, version, and description
- MCP protocol version and capabilities
- Authentication methods and requirements
- Skill catalog organized by functional category
- Required permissions and dependencies
- Endpoint configuration

### Available Skills

The agent provides **20 tools** organized into **6 skill categories**:

#### 1. Node Management
- `list_nodes` - List all cluster nodes
- `get_node_status` - Get node resource usage and status

#### 2. Virtual Machine Management
- `list_vms` - List VMs (node-specific or cluster-wide)
- `get_vm_config` - Get VM configuration
- `get_vm_status` - Get VM status and metrics
- `start_vm` - Start a VM
- `stop_vm` - Force stop a VM
- `shutdown_vm` - Gracefully shutdown a VM
- `reboot_vm` - Reboot a VM
- `create_vm_snapshot` - Create VM snapshot
- `list_vm_snapshots` - List VM snapshots
- `delete_vm_snapshot` - Delete VM snapshot

#### 3. Container Management
- `list_containers` - List LXC containers
- `get_container_status` - Get container status
- `start_container` - Start container
- `stop_container` - Stop container

#### 4. Storage Management
- `list_storage` - List storage devices
- `get_storage_status` - Get storage usage and capacity

#### 5. Task Management
- `list_tasks` - List running and recent tasks
- `get_task_status` - Get task progress and status

#### 6. Cluster Management
- `get_cluster_status` - Get overall cluster status and resources

### Agent-to-Agent Integration

#### Discovery

Other agents can discover this agent's capabilities by reading the agent card:

```python
import json

# Load agent card
with open('agent-card.json') as f:
    agent_card = json.load(f)

# Discover capabilities
print(f"Agent: {agent_card['name']}")
print(f"Version: {agent_card['version']}")
print(f"Skills: {len(agent_card['skills'])} categories")

# List available skills
for skill in agent_card['skills']:
    print(f"\n{skill['category']}:")
    for capability in skill['capabilities']:
        print(f"  - {capability['name']}: {capability['description']}")
```

#### Authentication Setup

Agents can programmatically configure authentication:

```python
# API Token (recommended)
env_config = {
    "PROXMOX_HOST": "192.168.1.100",
    "PROXMOX_USER": "root@pam",
    "PROXMOX_TOKEN_NAME": "automation",
    "PROXMOX_TOKEN_VALUE": "your-token-value"
}

# Or Password-based
env_config = {
    "PROXMOX_HOST": "192.168.1.100",
    "PROXMOX_USER": "root@pam",
    "PROXMOX_PASSWORD": "your-password"
}
```

#### Tool Invocation

Agents communicate via MCP protocol:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Connect to the agent
server_params = StdioServerParameters(
    command="uv",
    args=["--directory", "/path/to/proxmox-mcp-server", "run", "proxmox-mcp-server"],
    env=env_config
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        # Initialize session
        await session.initialize()

        # List available tools
        tools = await session.list_tools()

        # Call a tool
        result = await session.call_tool("list_vms", arguments={})
        print(result.content)
```

#### Multi-Agent Orchestration Example

Example workflow with multiple agents:

```python
# Agent orchestration: VM backup workflow
async def backup_workflow():
    # 1. Proxmox agent: List VMs
    vms = await proxmox_agent.call_tool("list_vms", {})

    # 2. Proxmox agent: Create snapshots for each VM
    for vm in vms['data']:
        snapshot_name = f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        await proxmox_agent.call_tool("create_vm_snapshot", {
            "node": vm['node'],
            "vmid": vm['vmid'],
            "snapname": snapshot_name
        })

    # 3. Storage agent: Verify backup storage capacity
    storage_status = await storage_agent.call_tool("check_capacity", {})

    # 4. Notification agent: Send completion report
    await notification_agent.call_tool("send_alert", {
        "message": f"Backup completed: {len(vms['data'])} VMs"
    })
```

### A2A Protocol Benefits

**For AI Agents:**
- **Self-documenting** - Agent card provides complete capability discovery
- **Type-safe** - Structured skill definitions with input/output schemas
- **Composable** - Skills can be combined for complex workflows
- **Secure** - Clear authentication requirements and permissions

**For Orchestration Systems:**
- **Dynamic discovery** - Find and integrate agents at runtime
- **Capability matching** - Match tasks to agent skills automatically
- **Parallel execution** - Coordinate multiple agents simultaneously
- **Error handling** - Standardized error responses and retry logic

### Integration Examples

#### Example 1: Infrastructure Monitoring Agent

```python
# Monitoring agent that uses Proxmox agent skills
async def monitor_infrastructure():
    # Get cluster status
    cluster = await proxmox_agent.call_tool("get_cluster_status", {})

    # Get all nodes
    nodes = await proxmox_agent.call_tool("list_nodes", {})

    # Check each node's status
    for node in nodes['data']:
        status = await proxmox_agent.call_tool("get_node_status", {
            "node": node['node']
        })

        # Alert if resource usage is high
        if status['data']['cpu'] > 0.9:
            await alert_agent.send_alert(f"High CPU on {node['node']}")
```

#### Example 2: Auto-scaling Agent

```python
# Auto-scaling agent that manages VM capacity
async def autoscale_vms():
    # Get current VM statuses
    vms = await proxmox_agent.call_tool("list_vms", {})

    # Analyze load across VMs
    for vm in vms['data']:
        status = await proxmox_agent.call_tool("get_vm_status", {
            "node": vm['node'],
            "vmid": vm['vmid']
        })

        # Scale based on metrics
        if needs_scaling(status):
            await proxmox_agent.call_tool("start_vm", {
                "node": "pve2",
                "vmid": get_next_vm_id()
            })
```

#### Example 3: Disaster Recovery Agent

```python
# DR agent that coordinates backup and recovery
async def disaster_recovery():
    # Take snapshots of all critical VMs
    critical_vms = [100, 101, 102]

    for vmid in critical_vms:
        # Find which node hosts the VM
        vms = await proxmox_agent.call_tool("list_vms", {})
        vm = next(v for v in vms['data'] if v['vmid'] == vmid)

        # Create snapshot
        await proxmox_agent.call_tool("create_vm_snapshot", {
            "node": vm['node'],
            "vmid": vmid,
            "snapname": f"dr-{datetime.now().isoformat()}"
        })

        # Verify snapshot
        snapshots = await proxmox_agent.call_tool("list_vm_snapshots", {
            "node": vm['node'],
            "vmid": vmid
        })
```

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
