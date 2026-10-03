<img src="https://github.com/ry-ops/proxmox-mcp-server/blob/main/proxmox-mcp-server.png" width="100%">

# Proxmox MCP Server

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-latest-green.svg)](https://github.com/astral-sh/uv)
[![MCP](https://img.shields.io/badge/MCP-1.0-purple.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/ry-ops/proxmox-mcp-server/pulls)

A Model Context Protocol (MCP) server for the Proxmox Virtual Environment API. It exposes **339 tools** covering nodes, VMs, containers, storage, clustering and HA, users and permissions, firewall, disks, Ceph, ACME certificates, SDN, notifications, resource pools and appliance deployment.

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

### Proxmox VE API Coverage

| Area | Tools | Highlights |
|------|------:|------------|
| Nodes | 38 | Status, config, DNS/hosts/time, network interfaces, services, APT updates, syslog, power |
| QEMU VMs | 46 | Lifecycle, create/clone/delete, config, snapshots, migration, disk resize/move, RRD metrics, guest agent (`vm_agent_exec`, `vm_agent_exec_status`), VNC proxy |
| LXC containers | 28 | Lifecycle, create/clone/delete, config, snapshots, migration, resize |
| Storage & backup | 14 | Storage definitions, content and volumes, URL downloads, `vzdump` backup and restore |
| Cluster | 37 | Status, resources, options, log, tasks, HA resources/groups, replication, backup jobs |
| Access control | 33 | Users, API tokens, groups, roles, ACLs, realms |
| Firewall | 31 | Cluster and node rules, security groups, aliases, IP sets, macros, logs (per-VM/container rules are in the guest modules) |
| Disks | 17 | SMART, wipe, GPT init, LVM, LVM-thin, ZFS, directory storage |
| Ceph | 33 | Status, OSDs, monitors, managers, MDS, pools, flags, CRUSH |
| ACME & certificates | 17 | ACME accounts and plugins, node certificate ordering, custom certs |
| SDN | 16 | Zones, VNets, subnets, apply |
| Notifications | 23 | Gotify, sendmail, SMTP and webhook endpoints, matchers |
| Pools | 5 | Resource pool CRUD |
| Appliances | 1 | `deploy_fortigate_vm`: FortiGate-VM from Fortinet's KVM image, WAN/LAN NICs on chosen bridges and VLANs, sized for the free evaluation license |

See [Available Tools](#available-tools) for how to browse the full list.

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

# Run setup script (installs dependencies)
./setup.sh

# Or manually:
uv sync
```

### Docker

A multi-arch image is published to GitHub Container Registry on every push to `main` and for each release tag:

```bash
docker pull ghcr.io/ry-ops/proxmox-mcp-server:latest   # or a version tag, e.g. :2.2.0
```

MCP clients talk to the server over stdio, so run the container interactively (`-i`) and pass configuration as environment variables:

```bash
docker run -i --rm --env-file .env ghcr.io/ry-ops/proxmox-mcp-server:latest
```

`docker-compose.yaml` in this repository does the same using your `.env` file (copy `.env.example` to get started).

## Configuration

The server is configured via environment variables:

### Required Variables

- `PROXMOX_HOST`: Proxmox server hostname or IP address, without scheme or port (e.g. `192.168.1.100`, not `https://192.168.1.100:8006`)
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
- `PROXMOX_READ_ONLY`: Block all writes — only GET requests are allowed; any create/update/delete/action tool is refused (default: `false`). 149 of the 339 tools are read-only and keep working. Three read-style tools also send POST requests and are blocked: `vm_agent_ping`, plus `get_vm_vnc_proxy` and `get_vm_spice_proxy`, which create console access tickets

When running from a clone, a `.env` file in the project directory is loaded automatically. See [`.env.example`](.env.example).

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

### With Docker

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "PROXMOX_HOST",
        "-e", "PROXMOX_USER",
        "-e", "PROXMOX_TOKEN_NAME",
        "-e", "PROXMOX_TOKEN_VALUE",
        "ghcr.io/ry-ops/proxmox-mcp-server:latest"
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

**Important**: For the `uv` configurations, use the absolute path to your project directory!

## Available Tools

The server registers 339 tools, grouped by API area in [`proxmox_mcp/tools/`](proxmox_mcp/tools/), one module per area. Tool names follow the Proxmox API: `list_*`, `get_*`, `create_*`, `update_*`/`set_*`, `delete_*`, plus actions such as `start_vm`, `migrate_container` or `apply_sdn`.

Some commonly used tools:

| Task | Tools |
|------|-------|
| Inventory | `list_nodes`, `get_cluster_resources`, `list_vms`, `list_containers`, `list_storage` |
| VM lifecycle | `start_vm`, `shutdown_vm`, `stop_vm`, `reboot_vm`, `create_vm`, `clone_vm`, `migrate_vm` |
| Disk images | `download_url_to_storage` with `content=import`, then `create_vm` with `scsi0=local-lvm:0,import-from=local:import/<image>` or `import_vm_disk` |
| Snapshots | `create_vm_snapshot`, `list_vm_snapshots`, `rollback_vm_snapshot`, `delete_vm_snapshot` |
| Monitoring | `get_node_status`, `get_vm_status`, `get_vm_rrddata`, `get_node_storage_status` |
| Tasks | `list_cluster_tasks`, `list_node_tasks`, `get_task_status`, `get_task_log` |
| Guest agent | `vm_agent_exec` (returns a PID), then `vm_agent_exec_status` for exit code and output |

Your MCP client lists every tool with its full input schema. To print them all locally:

```bash
uv run python -c "from proxmox_mcp.server import ALL_TOOLS; print('\n'.join(sorted(t.name for t in ALL_TOOLS)))"
```

See [USAGE.md](USAGE.md) for worked examples.

## Example Usage

Once configured, you can ask Claude to interact with your Proxmox environment:

> "Can you list all VMs in my Proxmox cluster?"

> "What's the status of VM 100 on node pve1?"

> "Start VM 105 on node pve1"

> "Create a snapshot called 'backup-2025' for VM 100 on pve1"

> "Show me the storage usage on all nodes"

> "List all running tasks in the cluster"

> "Clone VM 9000 to a new VM called web-02 and start it"

> "Run `df -h` inside VM 120 using the guest agent and show me the output"

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

# Lint and format (dev dependencies are installed by `uv sync`)
uv run ruff check .
uv run black .
```

## Project Structure

```
proxmox-mcp-server/
├── proxmox_mcp/
│   ├── server.py             # MCP server entrypoint and tool registry
│   ├── client.py             # Proxmox API client (token/password auth)
│   └── tools/                # Tool definitions and handlers, one module per API area
│       ├── nodes.py, qemu.py, lxc.py, storage.py, cluster.py, access.py
│       └── firewall.py, disks.py, ceph.py, acme.py, sdn.py, notifications.py, pools.py
├── Dockerfile                # Container image (stdio transport)
├── docker-compose.yaml       # Compose setup using .env
├── agent-card.json           # A2A agent card
├── pyproject.toml            # Project configuration
├── uv.lock                   # Locked dependencies
├── .env.example              # Environment variable template
├── setup.sh                  # Automated setup script
├── test-connection.sh        # Connection test script
├── README.md                 # This file
├── CHANGELOG.md              # Release history
├── QUICKSTART.md             # 5-minute setup guide
├── SETUP.md                  # Detailed setup guide
└── USAGE.md                  # Usage examples

```

## Security Considerations

- **API Tokens** are more secure than password authentication as they can be revoked independently
- For monitoring-only deployments, set `PROXMOX_READ_ONLY=true` *and* use a `PVEAuditor` token. The flag stops the server from sending writes, and the token permissions enforce the same limit on the Proxmox side
- Set `PROXMOX_VERIFY_SSL=true` in production environments with valid SSL certificates
- Grant minimal required permissions to API tokens. The server exposes destructive operations (deleting VMs, wiping disks, running commands inside guests via the agent), and the token's permissions are the only thing limiting what a connected AI client can do. For monitoring-only use, a token with the `PVEAuditor` role is enough
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

The agent card lists all **339 tools** in **14 skill categories**, generated from the server's tool registry. Each entry has the tool's name, description and inputs:

| Category | Tools |
|----------|------:|
| `node_management` | 38 |
| `virtual_machine_management` | 46 |
| `container_management` | 28 |
| `storage_management` | 14 |
| `cluster_management` | 37 |
| `access_control` | 33 |
| `firewall_management` | 31 |
| `disk_management` | 17 |
| `ceph_management` | 33 |
| `certificate_management` | 17 |
| `sdn_management` | 16 |
| `notification_management` | 23 |
| `pool_management` | 5 |

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

## API Documentation

For more information about the Proxmox VE API:
- [Proxmox VE API Documentation](https://pve.proxmox.com/wiki/Proxmox_VE_API)
- [API Viewer](https://pve.proxmox.com/pve-docs/api-viewer/)
- [Proxmox VE Administration Guide](https://pve.proxmox.com/pve-docs/pve-admin-guide.html)

## Dependencies

- **mcp** (>=1.0.0, <2): Model Context Protocol SDK. 2.x changed the server API and is not supported yet
- **httpx** (>=0.28.1): Async HTTP client for the Proxmox API
- **python-dotenv** (>=1.2.3): Loads configuration from `.env`

## Roadmap

- Streamable-HTTP transport for running the server as a network service ([#24](https://github.com/ry-ops/proxmox-mcp-server/pull/24), [#29](https://github.com/ry-ops/proxmox-mcp-server/pull/29))
- Support for `mcp` 2.x
- Automatic ticket refresh for long-running password-authenticated sessions
- Automated test suite

See [CHANGELOG.md](CHANGELOG.md) for what has shipped.

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

MIT. See [LICENSE](LICENSE).

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

<!-- org-footer -->
---

<p align="center"><sub>Part of <a href="https://github.com/ry-ops">ry-ops</a> · building the pipes between infrastructure, automation, and observability · built by <a href="https://github.com/ry-ops">ry-ops</a></sub></p>
