<img src="https://github.com/ry-ops/proxmox-mcp-server/blob/main/proxmox-mcp-server.png" width="100%">
## Proxmox MCP Server

A Model Context Protocol (MCP) server for interacting with Proxmox Virtual Environment API. This server provides comprehensive tools for managing VMs, containers, storage, and cluster resources through the MCP interface.

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

## Installation

```bash
npm install
npm run build
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
4. Copy the Token ID and Secret
5. Set appropriate permissions for the token

Example token format:
```
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

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "node",
      "args": ["/path/to/proxmox-mcp-server/build/index.js"],
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

Or using password authentication:

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "node",
      "args": ["/path/to/proxmox-mcp-server/build/index.js"],
      "env": {
        "PROXMOX_HOST": "192.168.1.100",
        "PROXMOX_USER": "root@pam",
        "PROXMOX_PASSWORD": "your-password-here"
      }
    }
  }
}
```

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

## Security Considerations

- **API Tokens** are more secure than password authentication as they can be revoked independently
- Set `PROXMOX_VERIFY_SSL=true` in production environments with valid SSL certificates
- Grant minimal required permissions to API tokens
- Store credentials securely and never commit them to version control
- Consider network restrictions (firewall rules) for API access

## API Documentation

For more information about the Proxmox VE API:
- [Proxmox VE API Documentation](https://pve.proxmox.com/wiki/Proxmox_VE_API)
- [API Viewer](https://pve.proxmox.com/pve-docs/api-viewer/)

## Troubleshooting

### Authentication Errors

- Verify your credentials are correct
- Check that the user has appropriate permissions
- For API tokens, ensure the token hasn't expired or been revoked

### Connection Errors

- Verify `PROXMOX_HOST` and `PROXMOX_PORT` are correct
- Check network connectivity to the Proxmox host
- If using SSL verification, ensure certificates are valid

### Permission Errors

- The user/token needs appropriate privileges for the operations
- Common required privileges: `VM.Monitor`, `VM.Audit`, `Datastore.Audit
