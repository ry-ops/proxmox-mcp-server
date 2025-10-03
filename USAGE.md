# Proxmox MCP Server - Usage Guide

Comprehensive guide with examples for using the Proxmox MCP Server with Claude AI.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Basic Usage Patterns](#basic-usage-patterns)
- [Virtual Machine Management](#virtual-machine-management)
- [Container Management](#container-management)
- [Snapshot Management](#snapshot-management)
- [Storage Management](#storage-management)
- [Node Management](#node-management)
- [Task Management](#task-management)
- [Cluster Management](#cluster-management)
- [Advanced Queries](#advanced-queries)
- [Tool Reference](#tool-reference)
- [Best Practices](#best-practices)
- [Common Workflows](#common-workflows)

---

## Getting Started

After configuring the MCP server in Claude Desktop, you can interact with your Proxmox infrastructure using natural language.

### First Commands

Try these to verify everything works:

```
List all nodes in my Proxmox cluster
```

```
Show me all VMs
```

```
What's the cluster status?
```

### Understanding Responses

Claude will use the Proxmox MCP tools to fetch information and present it clearly. You'll see:
- Formatted data from your Proxmox server
- Natural language explanations
- Status indicators
- Actionable suggestions

---

## Basic Usage Patterns

### Discovery Queries

**Find resources:**
```
List all nodes
```

```
Show me all virtual machines
```

```
List containers on pve1
```

```
What storage devices are available?
```

### Status Checks

**Check health:**
```
What's the status of VM 100 on pve1?
```

```
Is node pve1 healthy?
```

```
Show me resource usage across all nodes
```

```
Which VMs are currently running?
```

### Quick Actions

**Common operations:**
```
Start VM 100 on pve1
```

```
Shutdown VM 105 gracefully
```

```
Reboot VM 110 on pve1
```

```
Show me all running tasks
```

---

## Virtual Machine Management

### Listing VMs

**Cluster-wide:**
```
List all VMs in the cluster
```

```
Show me all virtual machines
```

**Node-specific:**
```
List VMs on node pve1
```

```
Show me all VMs on pve2
```

**Filtered queries:**
```
Which VMs are currently running?
```

```
Show me stopped VMs
```

```
List VMs with their memory allocation
```

### VM Status

**Single VM:**
```
What's the status of VM 100 on pve1?
```

```
Is VM 105 running on pve1?
```

```
Show me the current state of VM 110
```

**Multiple VMs:**
```
Check the status of VMs 100, 105, and 110 on pve1
```

```
Show me the status of all VMs on pve2
```

### VM Configuration

**View config:**
```
Show me the configuration for VM 100 on pve1
```

```
What are the specs of VM 105?
```

```
How much memory does VM 110 have?
```

**Detailed queries:**
```
Show me the CPU and memory configuration for VM 100
```

```
What disk setup does VM 105 have?
```

### VM Power Management

**Start VMs:**
```
Start VM 100 on pve1
```

```
Power on VM 105
```

**Stop VMs (forced):**
```
Stop VM 100 on pve1
```

```
Force stop VM 105 (it's not responding)
```

**Shutdown VMs (graceful):**
```
Shutdown VM 100 gracefully
```

```
Shutdown VM 105 on pve1 with 120 second timeout
```

**Reboot VMs:**
```
Reboot VM 100 on pve1
```

```
Restart VM 105
```

### Batch Operations

**Multiple VMs:**
```
Start VMs 100, 101, and 102 on pve1
```

```
Shutdown all VMs on pve1 gracefully
```

```
Show me the status of all VMs and indicate which need attention
```

---

## Container Management

### Listing Containers

```
List all containers on pve1
```

```
Show me all LXC containers on pve2
```

```
How many containers are running on pve1?
```

### Container Status

```
What's the status of container 200 on pve1?
```

```
Is container 201 running?
```

```
Show me details for container 205
```

### Container Operations

**Start containers:**
```
Start container 200 on pve1
```

```
Start container 201
```

**Stop containers:**
```
Stop container 200 on pve1
```

```
Stop container 201
```

### Container Queries

```
List all running containers
```

```
Which containers are stopped?
```

```
Show me container resource usage
```

---

## Snapshot Management

### Creating Snapshots

**Basic snapshot:**
```
Create a snapshot called "backup-2025-01-15" for VM 100 on pve1
```

```
Create a snapshot named "pre-update" for VM 105
```

**With description:**
```
Create a snapshot called "before-kernel-update" for VM 100 on pve1 with description "Snapshot before updating kernel from 5.15 to 6.1"
```

```
Snapshot VM 105 as "stable-config" with description "Working configuration before testing"
```

### Listing Snapshots

```
List all snapshots for VM 100 on pve1
```

```
Show me snapshots of VM 105
```

```
What snapshots exist for VM 110?
```

### Deleting Snapshots

```
Delete the snapshot "backup-2025-01-15" from VM 100 on pve1
```

```
Remove snapshot "old-backup" from VM 105
```

### Snapshot Workflows

**Before updates:**
```
Create a snapshot called "pre-update-$(date +%Y%m%d)" for VM 100 on pve1, then show me all snapshots
```

**Cleanup old snapshots:**
```
List all snapshots for VM 100, identify ones older than 30 days
```

---

## Storage Management

### Listing Storage

**All storage:**
```
List all storage devices
```

```
Show me all storage in the cluster
```

**Node-specific:**
```
List storage on pve1
```

```
Show me storage devices on pve2
```

### Storage Status

```
What's the status of storage "local-lvm" on pve1?
```

```
Show me the usage of storage "backup-storage"
```

```
How much free space is on "data-storage"?
```

### Storage Analysis

**Capacity checks:**
```
Which storage devices are more than 80% full?
```

```
Show me storage usage across all nodes
```

```
Which storage has the most free space?
```

**Monitoring:**
```
Show me storage capacity for all devices
```

```
List storage sorted by usage
```

```
Alert me if any storage is critically low
```

---

## Node Management

### Node Information

**List nodes:**
```
List all nodes in the cluster
```

```
Show me all Proxmox nodes
```

**Node status:**
```
What's the status of node pve1?
```

```
Show me resource usage on pve1
```

```
Is node pve2 healthy?
```

### Resource Monitoring

**CPU and Memory:**
```
What's the CPU usage on pve1?
```

```
Show me memory usage across all nodes
```

```
Which node has the most available resources?
```

**Overall health:**
```
Show me the health status of all nodes
```

```
Are there any nodes with high resource usage?
```

---

## Task Management

### Listing Tasks

**Recent tasks:**
```
List all running tasks
```

```
Show me recent tasks
```

```
What tasks are currently in progress?
```

**Limited results:**
```
Show me the last 10 tasks
```

```
List the 20 most recent tasks
```

**Node-specific:**
```
Show me tasks on pve1
```

```
List running tasks on pve2
```

### Task Status

```
Check the status of task UPID:pve1:0000ABCD...
```

```
What's the progress of the last backup task?
```

### Task Analysis

**Failed tasks:**
```
Show me any failed tasks
```

```
Are there any errors in recent tasks?
```

**Long-running tasks:**
```
Which tasks have been running for more than 10 minutes?
```

```
Show me active backup tasks
```

---

## Cluster Management

### Cluster Overview

```
Show me the cluster status
```

```
Give me an overview of cluster resources
```

```
What's the overall health of the cluster?
```

### Resource Summary

```
Show me total CPU and memory across the cluster
```

```
How many VMs and containers are in the cluster?
```

```
What's the total storage capacity?
```

### Cluster Analysis

```
Which node has the most VMs?
```

```
Show me resource distribution across nodes
```

```
Are resources balanced across the cluster?
```

---

## Advanced Queries

### Multi-Step Operations

**Sequential actions:**
```
Create a snapshot "pre-update" for VM 100, then show me all snapshots
```

```
Shutdown VM 105 gracefully, wait for it to stop, then show me its status
```

```
Start all stopped VMs on pve1, then list their status
```

### Conditional Logic

```
Check if VM 100 is running, and if so, create a snapshot before updating
```

```
If VM 105 is stopped, start it and verify it's running
```

```
Show me which VMs need snapshots (ones without recent snapshots)
```

### Complex Analysis

**Resource planning:**
```
Show me which nodes have capacity for a new VM with 8GB RAM and 4 CPUs
```

```
Analyze storage usage trends and predict when storage will be full
```

**Health monitoring:**
```
Give me a health report for all VMs including status, uptime, and resource usage
```

```
Identify any VMs or containers with potential issues
```

### Reporting

**Status reports:**
```
Create a status report for all VMs showing name, status, node, memory, and CPU
```

```
Generate a summary report of cluster resources
```

**Inventory:**
```
Create an inventory of all VMs with their configurations
```

```
List all storage devices with capacity and usage
```

---

## Tool Reference

### Complete Tool List

The MCP server provides 20 tools:

#### Node Tools (2)
- `list_nodes` - List all cluster nodes
- `get_node_status` - Get node resource usage

#### VM Tools (10)
- `list_vms` - List virtual machines
- `get_vm_config` - Get VM configuration
- `get_vm_status` - Get VM current status
- `start_vm` - Start a VM
- `stop_vm` - Force stop a VM
- `shutdown_vm` - Graceful VM shutdown
- `reboot_vm` - Reboot a VM
- `create_vm_snapshot` - Create VM snapshot
- `list_vm_snapshots` - List VM snapshots
- `delete_vm_snapshot` - Delete VM snapshot

#### Container Tools (4)
- `list_containers` - List LXC containers
- `get_container_status` - Get container status
- `start_container` - Start container
- `stop_container` - Stop container

#### Storage Tools (2)
- `list_storage` - List storage devices
- `get_storage_status` - Get storage status

#### Task Tools (2)
- `list_tasks` - List running/recent tasks
- `get_task_status` - Get specific task status

#### Cluster Tools (1)
- `get_cluster_status` - Get cluster resources

### Tool Parameters

**Node operations:**
- `node` (string): Node name (e.g., "pve1")

**VM operations:**
- `node` (string, required): Node name
- `vmid` (integer, required): VM ID
- `timeout` (integer, optional): Timeout in seconds
- `snapname` (string): Snapshot name
- `description` (string, optional): Snapshot description

**Container operations:**
- `node` (string, required): Node name
- `vmid` (integer, required): Container ID

**Storage operations:**
- `node` (string, optional): Node name
- `storage` (string): Storage ID

**Task operations:**
- `node` (string, optional): Node name
- `upid` (string): Task UPID
- `limit` (integer, optional): Max results

---

## Best Practices

### 1. Descriptive Snapshot Names

❌ **Poor:**
```
Create a snapshot "snap1" for VM 100
```

✅ **Good:**
```
Create a snapshot "backup-before-update-2025-01-15" for VM 100 on pve1 with description "Pre-kernel update backup"
```

### 2. Graceful Shutdowns

❌ **Poor:**
```
Stop VM 100
```

✅ **Good:**
```
Shutdown VM 100 gracefully with 120 second timeout
```

Use `stop_vm` only when necessary:
```
VM 100 is not responding, force stop it
```

### 3. Verify Before Acting

❌ **Poor:**
```
Start all VMs
```

✅ **Good:**
```
Show me which VMs are stopped, then start them one by one
```

### 4. Use Clear Node References

❌ **Poor:**
```
What's the status of VM 100?
```

✅ **Good:**
```
What's the status of VM 100 on pve1?
```

### 5. Monitor Long-Running Operations

✅ **Good:**
```
Start VM 100, then check the task status
```

```
Create snapshot for VM 100, show me when it's complete
```

### 6. Regular Health Checks

**Daily:**
```
Show me cluster status and any issues
```

**Weekly:**
```
List all snapshots and identify old ones for cleanup
```

```
Show me storage usage trends
```

**Monthly:**
```
Create a comprehensive cluster health report
```

---

## Common Workflows

### 1. System Update Workflow

```
1. "Create a snapshot 'pre-update-2025-01-15' for VM 100 on pve1"
2. "Shutdown VM 100 gracefully"
3. "Wait for VM 100 to stop"
4. Perform updates manually
5. "Start VM 100 on pve1"
6. "Check the status of VM 100"
7. If successful: "Delete the snapshot 'pre-update-2025-01-15'"
```

### 2. Daily Health Check

```
1. "Show me cluster status"
2. "List all running tasks"
3. "Which storage devices are above 80% capacity?"
4. "Are there any stopped VMs that should be running?"
5. "Show me any failed tasks from the last 24 hours"
```

### 3. New VM Deployment

```
1. "Which nodes have available capacity?"
2. "Show me storage on pve1"
3. Deploy VM manually
4. "List VMs on pve1 to confirm"
5. "Start VM 150 on pve1"
6. "Check the status of VM 150"
```

### 4. Maintenance Window

```
1. "List all VMs on pve1"
2. "Create snapshots for all VMs on pve1"
3. "Shutdown all VMs on pve1 gracefully"
4. Perform maintenance
5. "Start all VMs on pve1"
6. "Verify all VMs are running"
```

### 5. Storage Management

```
1. "Show me all storage devices"
2. "Which storage is most full?"
3. "List VMs on the full storage"
4. "Show me recent tasks related to storage"
```

### 6. Troubleshooting

```
1. "Is VM 100 running?"
2. "Show me the configuration for VM 100"
3. "List recent tasks for VM 100"
4. "Check node pve1 status"
5. "Show me any error messages"
```

### 7. Snapshot Cleanup

```
1. "List all snapshots for VM 100"
2. "Which snapshots are older than 30 days?"
3. "Delete old snapshots one by one"
4. "Verify remaining snapshots"
```

### 8. Capacity Planning

```
1. "Show me resource usage across all nodes"
2. "Which node has the most free memory?"
3. "Show me storage capacity on all devices"
4. "How many VMs can we fit with current resources?"
```

---

## Tips and Tricks

### Natural Language Flexibility

Claude understands various phrasings:

```
"List all nodes"
"Show me the nodes"
"What nodes do I have?"
"Display cluster nodes"
```

All produce the same result!

### Be Specific When Needed

For faster, more accurate responses:
- Include node names: "on pve1"
- Use VM IDs: "VM 100"
- Specify timeframes: "in the last hour"

### Ask Follow-Up Questions

```
User: "Show me all VMs"
Claude: [Shows VM list]
User: "What's the status of VM 100?"
Claude: [Shows VM 100 status]
User: "Start it"
Claude: [Starts VM 100]
```

### Request Summaries

```
"Summarize cluster health in 3 bullet points"
```

```
"Give me a TLDR of storage usage"
```

### Ask for Explanations

```
"What does VM status 'qmpstatus: stopped' mean?"
```

```
"Explain the difference between stop and shutdown"
```

---

## Error Handling

Claude will help you understand and resolve errors:

```
User: "Start VM 999 on pve1"
Claude: "I got an error - VM 999 doesn't exist on pve1. 
        Let me list the available VMs..."
```

```
User: "Shutdown VM 100"
Claude: "I need to know which node VM 100 is on. 
        Let me check... VM 100 is on pve1. 
        Shutting it down now..."
```

---

## Getting Help

If you're unsure what to ask:

```
"What can you help me with for Proxmox?"
```

```
"Show me examples of what I can do"
```

```
"How do I manage VMs?"
```

---

## Additional Resources

- [GitHub Repository](https://github.com/ry-ops/proxmox-mcp-server)
- [Quick Start Guide](QUICKSTART.md)
- [Setup Guide](SETUP.md)
- [Proxmox API Documentation](https://pve.proxmox.com/pve-docs/api-viewer/)

---

**Questions?** Open an issue on [GitHub](https://github.com/ry-ops/proxmox-mcp-server/issues)

## Common Usage Patterns

### Cluster Overview

**Get a complete picture of your cluster:**

```
Show me an overview of my Proxmox cluster including all nodes, VMs, and storage
```

Claude will use multiple tools:
- `get_cluster_status` - Overall resources
- `list_nodes` - All nodes
- `list_vms` - All VMs across the cluster
- `list_storage` - Storage devices

### Virtual Machine Management

**List all VMs:**
```
List all virtual machines in my cluster
```

**Check specific VM status:**
```
What's the status of VM 100 on node pve1?
```

**Start a VM:**
```
Start VM 105 on pve1
```

**Graceful shutdown:**
```
Shutdown VM 105 on pve1 gracefully with a 60 second timeout
```

**Force stop a VM:**
```
Force stop VM 105 on pve1
```

**Get VM configuration:**
```
Show me the configuration for VM 100 on pve1
```

### Container Management

**List containers:**
```
List all LXC containers on node pve1
```

**Container operations:**
```
Start container 200 on pve1
```

```
What's the status of container 201 on pve1?
```

### Snapshot Management

**Create a snapshot:**
```
Create a snapshot called "before-update" for VM 100 on pve1 with description "Backup before system update"
```

**List snapshots:**
```
Show me all snapshots for VM 100 on pve1
```

**Delete a snapshot:**
```
Delete the snapshot "before-update" from VM 100 on pve1
```

### Storage Management

**View storage:**
```
Show me all storage devices and their usage
```

**Check specific storage:**
```
What's the status of storage "local-lvm" on node pve1?
```

### Node Management

**Node status:**
```
What's the current resource usage on node pve1?
```

**Compare nodes:**
```
Compare the resource usage across all nodes in my cluster
```

### Task Management

**View running tasks:**
```
Show me all currently running tasks
```

**Recent tasks:**
```
List the last 20 tasks across the cluster
```

**Task status:**
```
Check the status of task UPID:pve1:0000ABCD...
```

## Advanced Queries

### Multi-Step Operations

Claude can chain multiple operations together:

```
Create a snapshot called "backup-jan" for VM 100, then show me all snapshots
```

```
Shutdown VM 105, wait for it to stop, then show me its status
```

### Conditional Operations

```
Check if VM 100 is running, and if so, create a snapshot before updating
```

### Reporting

```
Create a report of all VMs showing their name, status, memory, and CPU allocation
```

```
Show me which nodes are running low on storage
```

```
List all stopped VMs across the cluster
```

### Monitoring

```
Show me all VMs with high CPU usage
```

```
Which storage devices are more than 80% full?
```

```
Are there any failed tasks in the last hour?
```

## Tool Reference

### Node Tools

#### list_nodes
Lists all nodes in the Proxmox cluster.

**Parameters:** None

**Example:**
```
List all nodes
```

**Response includes:** Node name, status, CPU, memory, uptime

#### get_node_status
Gets detailed status for a specific node.

**Parameters:**
- `node` (string, required): Node name

**Example:**
```
Show me the status of node pve1
```

**Response includes:** CPU usage, memory usage, disk usage, uptime, kernel version

### Virtual Machine Tools

#### list_vms
Lists all VMs, optionally filtered by node.

**Parameters:**
- `node` (string, optional): Node name to filter by

**Examples:**
```
List all VMs
```
```
List VMs on node pve1
```

#### get_vm_config
Gets the configuration of a VM.

**Parameters:**
- `node` (string, required): Node name
- `vmid` (number, required): VM ID

**Example:**
```
Show me the config for VM 100 on pve1
```

#### get_vm_status
Gets current status of a VM.

**Parameters:**
- `node` (string, required): Node name
- `vmid` (number, required): VM ID

**Example:**
```
What's the status of VM 100 on pve1?
```

#### start_vm
Starts a virtual machine.

**Parameters:**
- `node` (string, required): Node name
- `vmid` (number, required): VM ID

**Example:**
```
Start VM 100 on pve1
```

#### stop_vm
Force stops a VM (equivalent to pulling the power).

**Parameters:**
- `node` (string, required): Node name
- `vmid` (number, required): VM ID
- `timeout` (number, optional): Timeout in seconds

**Example:**
```
Stop VM 100 on pve1
```

#### shutdown_vm
Gracefully shuts down a VM.

**Parameters:**
- `node` (string, required): Node name
- `vmid` (number, required): VM ID
- `timeout` (number, optional): Timeout in seconds

**Example:**
```
Shutdown VM 100 on pve1 with 120 second timeout
```

#### reboot_vm
Reboots a VM.

**Parameters:**
- `node` (string, required): Node name
- `vmid` (number, required): VM ID

**Example:**
```
Reboot VM 100 on pve1
```

### Container Tools

#### list_containers
Lists all LXC containers on a node.

**Parameters:**
- `node` (string, required): Node name

**Example:**
```
List containers on pve1
```

#### get_container_status
Gets status of an LXC container.

**Parameters:**
- `node` (string, required): Node name
- `vmid` (number, required): Container ID

**Example:**
```
What's the status of container 200 on pve1?
```

#### start_container
Starts a container.

**Parameters:**
- `node` (string, required): Node name
- `vmid` (number, required): Container ID

**Example:**
```
Start container 200 on pve1
```

#### stop_container
Stops a container.

**Parameters:**
- `node` (string, required): Node name
- `vmid` (number, required): Container ID

**Example:**
```
Stop container 200 on pve1
```

### Storage Tools

#### list_storage
Lists all storage devices.

**Parameters:**
- `node` (string, optional): Node name to filter by

**Examples:**
```
List all storage
```
```
List storage on pve1
```

#### get_storage_status
Gets status of a specific storage device.

**Parameters:**
- `node` (string, required): Node name
- `storage` (string, required): Storage ID

**Example:**
```
Show me the status of storage local-lvm on pve1
```

### Snapshot Tools

#### create_vm_snapshot
Creates a snapshot of a VM.

**Parameters:**
- `node` (string, required): Node name
- `vmid` (number, required): VM ID
- `snapname` (string, required): Snapshot name
- `description` (string, optional): Snapshot description

**Example:**
```
Create a snapshot called "backup-2025" for VM 100 on pve1
```

#### list_vm_snapshots
Lists all snapshots of a VM.

**Parameters:**
- `node` (string, required): Node name
- `vmid` (number, required): VM ID

**Example:**
```
List snapshots for VM 100 on pve1
```

#### delete_vm_snapshot
Deletes a VM snapshot.

**Parameters:**
- `node` (string, required): Node name
- `vmid` (number, required): VM ID
- `snapname` (string, required): Snapshot name

**Example:**
```
Delete the snapshot "backup-2025" from VM 100 on pve1
```

### Task Tools

#### list_tasks
Lists running and recent tasks.

**Parameters:**
- `node` (string, optional): Node name to filter by
- `limit` (number, optional): Maximum number of tasks (default: 50)

**Examples:**
```
Show me running tasks
```
```
List the last 30 tasks on pve1
```

#### get_task_status
Gets status of a specific task.

**Parameters:**
- `node` (string, required): Node name
- `upid` (string, required): Task UPID

**Example:**
```
Check status of task UPID:pve1:0000ABCD:...
```

### Cluster Tools

#### get_cluster_status
Gets overall cluster status and resources.

**Parameters:** None

**Example:**
```
Show me the cluster status
```

## Best Practices

### 1. Use Descriptive Snapshot Names

Instead of:
```
Create a snapshot called "snap1" for VM 100
```

Use:
```
Create a snapshot called "pre-kernel-update-2025-01" for VM 100 with description "Before updating from kernel 5.15 to 6.1"
```

### 2. Graceful Shutdowns

Prefer `shutdown_vm` over `stop_vm` when possible:
```
Shutdown VM 100 gracefully
```

Use `stop_vm` only when necessary:
```
Force stop VM 100 (it's not responding)
```

### 3. Check Before Acting

For critical operations, check status first:
```
Show me the status of VM 100, then shut it down gracefully
```

### 4. Monitor Long-Running Tasks

```
Start VM 100, then show me the task status
```

### 5. Resource Monitoring

Regularly check cluster resources:
```
Show me an overview of cluster resources and alert me if anything is over 90% utilized
```

## Troubleshooting

### "Error: HTTP 401"
- Check your authentication credentials
- Verify API token hasn't expired
- Ensure user has appropriate permissions

### "Error: HTTP 403"
- User/token lacks required permissions
- Check Proxmox permissions for the user/token
- Common needed permissions: VM.Monitor, VM.Audit, Datastore.Audit, Sys.Audit

### "Error: HTTP 500"
- Internal Proxmox error
- Check Proxmox logs: `/var/log/pve/tasks/`
- Verify the node is healthy

### "Connection refused"
- Check PROXMOX_HOST and PROXMOX_PORT
- Verify network connectivity
- Check if Proxmox web interface is accessible

### Tool Not Available
- Restart Claude Desktop after configuration changes
- Check stderr output for authentication errors
- Verify the server is running correctly

## Security Tips

1. **Use API Tokens**: More secure than password authentication
2. **Minimal Permissions**: Grant only required permissions
3. **Token Expiration**: Set expiration dates on tokens
4. **Regular Audits**: Review API token usage regularly
5. **Secure Storage**: Never commit credentials to version control
6. **Network Security**: Use firewall rules to restrict API access
7. **SSL Verification**: Enable in production with valid certificates

## Performance Tips

1. **Filter by Node**: When possible, specify the node to reduce API calls
2. **Limit Results**: Use the `limit` parameter for task lists
3. **Batch Operations**: Ask Claude to perform multiple operations in sequence
4. **Cache Results**: Claude can remember results within a conversation

## Integration Examples

### With Automation Scripts

You can ask Claude to help create automation workflows:
```
Help me create a procedure for updating VM 100: create snapshot, shutdown, wait, update, start
```

### With Monitoring

```
Check all VMs and let me know which ones are using more than 80% memory
```

### With Maintenance

```
List all VMs, identify which ones can be updated today (not running critical services)
```

## Getting Help

If you encounter issues:
1. Check the main README.md for configuration
2. Review Proxmox API documentation
3. Check Claude Desktop logs
4. Verify Proxmox server logs
5. Test API access with `curl` or `pvesh`

## Example Session

Here's a complete example session managing VMs:

**User:** "Show me all VMs in my cluster"

**Claude:** *Uses list_vms tool* "You have 5 VMs across 2 nodes..."

**User:** "Which ones are currently running?"

**Claude:** "Based on the status, VMs 100, 102, and 105 are running..."

**User:** "Create a snapshot of VM 100 called 'backup-before-update'"

**Claude:** *Uses create_vm_snapshot* "Snapshot created successfully..."

**User:** "Now gracefully shutdown VM 100"

**Claude:** *Uses shutdown_vm* "VM 100 is shutting down..."

**User:** "Check if it's stopped"

**Claude:** *Uses get_vm_status* "VM 100 is now stopped..."

**User:** "List all snapshots for VM 100"

**Claude:** *Uses list_vm_snapshots* "VM 100 has 2 snapshots: 'backup-before-update' and 'backup-weekly'..."
