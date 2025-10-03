#!/usr/bin/env python3
"""
Proxmox VE MCP Server

An MCP server for interacting with Proxmox Virtual Environment API.
Provides tools for managing VMs, containers, nodes, storage, and more.

GitHub: https://github.com/ry-ops/proxmox-mcp-server
Documentation: https://github.com/ry-ops/proxmox-mcp-server#readme

Configuration via environment variables:
    PROXMOX_HOST: Proxmox server hostname/IP (required)
    PROXMOX_PORT: API port (default: 8006)
    PROXMOX_USER: Username (e.g., root@pam) (required)
    PROXMOX_TOKEN_NAME: Token name for API token auth (optional)
    PROXMOX_TOKEN_VALUE: Token value for API token auth (optional)
    PROXMOX_PASSWORD: Password for ticket auth (optional, if not using token)
    PROXMOX_VERIFY_SSL: Verify SSL certificates (default: false)

Author: ry-ops
License: MIT
Version: 1.0.0
"""

import os
import json
import sys
import httpx
import asyncio
from typing import Any, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

# Configuration
PROXMOX_HOST = os.getenv("PROXMOX_HOST")
PROXMOX_PORT = os.getenv("PROXMOX_PORT", "8006")
PROXMOX_USER = os.getenv("PROXMOX_USER")
PROXMOX_TOKEN_NAME = os.getenv("PROXMOX_TOKEN_NAME")
PROXMOX_TOKEN_VALUE = os.getenv("PROXMOX_TOKEN_VALUE")
PROXMOX_PASSWORD = os.getenv("PROXMOX_PASSWORD")
PROXMOX_VERIFY_SSL = os.getenv("PROXMOX_VERIFY_SSL", "false").lower() == "true"

# Validate required configuration
if not PROXMOX_HOST or not PROXMOX_USER:
    print("Error: PROXMOX_HOST and PROXMOX_USER must be set", file=sys.stderr)
    sys.exit(1)

# Check authentication method
use_token_auth = PROXMOX_TOKEN_NAME and PROXMOX_TOKEN_VALUE
use_password_auth = PROXMOX_PASSWORD

if not use_token_auth and not use_password_auth:
    print(
        "Error: Either token (PROXMOX_TOKEN_NAME + PROXMOX_TOKEN_VALUE) or PROXMOX_PASSWORD must be set",
        file=sys.stderr,
    )
    sys.exit(1)


class ProxmoxClient:
    """
    Client for interacting with Proxmox VE API.
    
    Handles authentication (token or password) and API requests.
    """

    def __init__(self):
        """Initialize the Proxmox API client."""
        self.base_url = f"https://{PROXMOX_HOST}:{PROXMOX_PORT}/api2/json"
        self.client = httpx.AsyncClient(verify=PROXMOX_VERIFY_SSL, timeout=30.0)
        self.ticket: Optional[str] = None
        self.csrf_token: Optional[str] = None
        self.token: Optional[str] = None

    async def authenticate(self) -> None:
        """
        Authenticate with Proxmox API using token or password.
        
        Raises:
            httpx.HTTPError: If authentication fails
        """
        if use_token_auth:
            # Use API token authentication
            self.token = f"PVEAPIToken={PROXMOX_USER}!{PROXMOX_TOKEN_NAME}={PROXMOX_TOKEN_VALUE}"
            print(f"✓ Using API token authentication for {PROXMOX_USER}", file=sys.stderr)
        else:
            # Use ticket authentication
            try:
                response = await self.client.post(
                    f"{self.base_url}/access/ticket",
                    data={"username": PROXMOX_USER, "password": PROXMOX_PASSWORD},
                )
                response.raise_for_status()
                data = response.json()["data"]
                self.ticket = data["ticket"]
                self.csrf_token = data["CSRFPreventionToken"]
                print(f"✓ Authenticated with ticket for {PROXMOX_USER}", file=sys.stderr)
            except Exception as e:
                print(f"✗ Authentication failed: {e}", file=sys.stderr)
                raise

    async def request(
        self, method: str, path: str, data: Optional[dict] = None
    ) -> dict:
        """
        Make an authenticated request to Proxmox API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API endpoint path
            data: Optional request data
            
        Returns:
            JSON response from API
            
        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.base_url}{path}"
        headers = {}

        # Add authentication headers
        if self.token:
            headers["Authorization"] = self.token
        elif self.ticket:
            headers["Cookie"] = f"PVEAuthCookie={self.ticket}"
            if method != "GET":
                headers["CSRFPreventionToken"] = self.csrf_token

        # Make request
        try:
            if method == "GET":
                response = await self.client.get(url, headers=headers, params=data)
            elif method == "POST":
                response = await self.client.post(url, headers=headers, data=data)
            elif method == "PUT":
                response = await self.client.put(url, headers=headers, data=data)
            elif method == "DELETE":
                response = await self.client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"✗ API request failed: {method} {path} - {e}", file=sys.stderr)
            raise

    async def get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make a GET request."""
        return await self.request("GET", path, params)

    async def post(self, path: str, data: Optional[dict] = None) -> dict:
        """Make a POST request."""
        return await self.request("POST", path, data)

    async def put(self, path: str, data: Optional[dict] = None) -> dict:
        """Make a PUT request."""
        return await self.request("PUT", path, data)

    async def delete(self, path: str) -> dict:
        """Make a DELETE request."""
        return await self.request("DELETE", path)

    async def close(self):
        """Close the HTTP client connection."""
        await self.client.aclose()


# Initialize client
proxmox = ProxmoxClient()

# Initialize MCP server
app = Server("proxmox-mcp-server")


# Define tools
TOOLS = [
    Tool(
        name="list_nodes",
        description="List all nodes in the Proxmox cluster",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_node_status",
        description="Get status and resource usage for a specific node",
        inputSchema={
            "type": "object",
            "properties": {"node": {"type": "string", "description": "Node name"}},
            "required": ["node"],
        },
    ),
    Tool(
        name="list_vms",
        description="List all virtual machines (QEMU/KVM) on a node or cluster-wide",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {
                    "type": "string",
                    "description": "Node name (optional, if not provided lists all VMs cluster-wide)",
                }
            },
        },
    ),
    Tool(
        name="get_vm_config",
        description="Get configuration for a specific VM",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="get_vm_status",
        description="Get current status of a VM",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="start_vm",
        description="Start a virtual machine",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="stop_vm",
        description="Stop a virtual machine (forced shutdown)",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (optional)",
                },
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="shutdown_vm",
        description="Gracefully shutdown a virtual machine (ACPI shutdown)",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (optional)",
                },
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="reboot_vm",
        description="Reboot a virtual machine",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="list_containers",
        description="List all LXC containers on a node",
        inputSchema={
            "type": "object",
            "properties": {"node": {"type": "string", "description": "Node name"}},
            "required": ["node"],
        },
    ),
    Tool(
        name="get_container_status",
        description="Get status of an LXC container",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "Container ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="start_container",
        description="Start an LXC container",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "Container ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="stop_container",
        description="Stop an LXC container",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "Container ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="list_storage",
        description="List all storage devices",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {
                    "type": "string",
                    "description": "Node name (optional, omit for cluster-wide)",
                }
            },
        },
    ),
    Tool(
        name="get_storage_status",
        description="Get status of a specific storage device",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "storage": {"type": "string", "description": "Storage ID"},
            },
            "required": ["node", "storage"],
        },
    ),
    Tool(
        name="list_tasks",
        description="List running and recent tasks",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {
                    "type": "string",
                    "description": "Node name (optional, omit for cluster-wide)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of tasks to return (default: 50)",
                },
            },
        },
    ),
    Tool(
        name="get_task_status",
        description="Get status of a specific task",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "upid": {"type": "string", "description": "Task UPID"},
            },
            "required": ["node", "upid"],
        },
    ),
    Tool(
        name="create_vm_snapshot",
        description="Create a snapshot of a VM",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
                "snapname": {"type": "string", "description": "Snapshot name"},
                "description": {
                    "type": "string",
                    "description": "Snapshot description (optional)",
                },
            },
            "required": ["node", "vmid", "snapname"],
        },
    ),
    Tool(
        name="list_vm_snapshots",
        description="List all snapshots of a VM",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="delete_vm_snapshot",
        description="Delete a VM snapshot",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
                "snapname": {"type": "string", "description": "Snapshot name"},
            },
            "required": ["node", "vmid", "snapname"],
        },
    ),
    Tool(
        name="get_cluster_status",
        description="Get overall cluster status and resources",
        inputSchema={"type": "object", "properties": {}},
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Handle tool execution requests from MCP client.
    
    Args:
        name: Tool name to execute
        arguments: Tool arguments
        
    Returns:
        List of TextContent with JSON response or error
    """
    try:
        result = None

        # Node operations
        if name == "list_nodes":
            result = await proxmox.get("/nodes")

        elif name == "get_node_status":
            result = await proxmox.get(f"/nodes/{arguments['node']}/status")

        # VM operations
        elif name == "list_vms":
            if "node" in arguments and arguments["node"]:
                result = await proxmox.get(f"/nodes/{arguments['node']}/qemu")
            else:
                # Get all nodes and collect VMs from each
                nodes_result = await proxmox.get("/nodes")
                all_vms = []
                for node in nodes_result["data"]:
                    vms = await proxmox.get(f"/nodes/{node['node']}/qemu")
                    for vm in vms["data"]:
                        vm["node"] = node["node"]
                        all_vms.append(vm)
                result = {"data": all_vms}

        elif name == "get_vm_config":
            result = await proxmox.get(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/config"
            )

        elif name == "get_vm_status":
            result = await proxmox.get(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/status/current"
            )

        elif name == "start_vm":
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/status/start"
            )

        elif name == "stop_vm":
            data = {}
            if "timeout" in arguments:
                data["timeout"] = arguments["timeout"]
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/status/stop",
                data,
            )

        elif name == "shutdown_vm":
            data = {}
            if "timeout" in arguments:
                data["timeout"] = arguments["timeout"]
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/status/shutdown",
                data,
            )

        elif name == "reboot_vm":
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/status/reboot"
            )

        # Container operations
        elif name == "list_containers":
            result = await proxmox.get(f"/nodes/{arguments['node']}/lxc")

        elif name == "get_container_status":
            result = await proxmox.get(
                f"/nodes/{arguments['node']}/lxc/{arguments['vmid']}/status/current"
            )

        elif name == "start_container":
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/lxc/{arguments['vmid']}/status/start"
            )

        elif name == "stop_container":
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/lxc/{arguments['vmid']}/status/stop"
            )

        # Storage operations
        elif name == "list_storage":
            if "node" in arguments and arguments["node"]:
                result = await proxmox.get(f"/nodes/{arguments['node']}/storage")
            else:
                result = await proxmox.get("/storage")

        elif name == "get_storage_status":
            result = await proxmox.get(
                f"/nodes/{arguments['node']}/storage/{arguments['storage']}/status"
            )

        # Task operations
        elif name == "list_tasks":
            params = {}
            if "limit" in arguments:
                params["limit"] = arguments["limit"]

            if "node" in arguments and arguments["node"]:
                result = await proxmox.get(
                    f"/nodes/{arguments['node']}/tasks", params
                )
            else:
                result = await proxmox.get("/cluster/tasks", params)

        elif name == "get_task_status":
            result = await proxmox.get(
                f"/nodes/{arguments['node']}/tasks/{arguments['upid']}/status"
            )

        # Snapshot operations
        elif name == "create_vm_snapshot":
            data = {"snapname": arguments["snapname"]}
            if "description" in arguments:
                data["description"] = arguments["description"]
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/snapshot",
                data,
            )

        elif name == "list_vm_snapshots":
            result = await proxmox.get(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/snapshot"
            )

        elif name == "delete_vm_snapshot":
            result = await proxmox.delete(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/snapshot/{arguments['snapname']}"
            )

        # Cluster operations
        elif name == "get_cluster_status":
            result = await proxmox.get("/cluster/resources")

        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        print(f"✗ {error_msg}", file=sys.stderr)
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]


async def main():
    """
    Main entry point for the Proxmox MCP server.
    
    Authenticates with Proxmox and starts the MCP server on stdio.
    """
    try:
        # Print startup information
        print("=" * 50, file=sys.stderr)
        print("Proxmox MCP Server v1.0.0", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        print(f"Proxmox Host: {PROXMOX_HOST}:{PROXMOX_PORT}", file=sys.stderr)
        print(f"User: {PROXMOX_USER}", file=sys.stderr)
        print(f"SSL Verification: {'Enabled' if PROXMOX_VERIFY_SSL else 'Disabled'}", file=sys.stderr)
        print(f"Authentication: {'API Token' if use_token_auth else 'Password'}", file=sys.stderr)
        print("=" * 50, file=sys.stderr)

        # Authenticate with Proxmox
        await proxmox.authenticate()

        print("=" * 50, file=sys.stderr)
        print("✓ Server ready - 20 tools available", file=sys.stderr)
        print("=" * 50, file=sys.stderr)

        # Run the MCP server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )

    except KeyboardInterrupt:
        print("\n✓ Server stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await proxmox.close()


if __name__ == "__main__":
    asyncio.run(main()) "description": "Timeout in seconds (optional)"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="reboot_vm",
        description="Reboot a virtual machine",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="list_containers",
        description="List all LXC containers on a node",
        inputSchema={
            "type": "object",
            "properties": {"node": {"type": "string", "description": "Node name"}},
            "required": ["node"],
        },
    ),
    Tool(
        name="get_container_status",
        description="Get status of an LXC container",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "Container ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="start_container",
        description="Start an LXC container",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "Container ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="stop_container",
        description="Stop an LXC container",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "Container ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="list_storage",
        description="List all storage devices",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name (optional)"}
            },
        },
    ),
    Tool(
        name="get_storage_status",
        description="Get status of a specific storage",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "storage": {"type": "string", "description": "Storage ID"},
            },
            "required": ["node", "storage"],
        },
    ),
    Tool(
        name="list_tasks",
        description="List running and recent tasks",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name (optional)"},
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of tasks to return (default: 50)",
                },
            },
        },
    ),
    Tool(
        name="get_task_status",
        description="Get status of a specific task",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "upid": {"type": "string", "description": "Task UPID"},
            },
            "required": ["node", "upid"],
        },
    ),
    Tool(
        name="create_vm_snapshot",
        description="Create a snapshot of a VM",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
                "snapname": {"type": "string", "description": "Snapshot name"},
                "description": {
                    "type": "string",
                    "description": "Snapshot description (optional)",
                },
            },
            "required": ["node", "vmid", "snapname"],
        },
    ),
    Tool(
        name="list_vm_snapshots",
        description="List all snapshots of a VM",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
            },
            "required": ["node", "vmid"],
        },
    ),
    Tool(
        name="delete_vm_snapshot",
        description="Delete a VM snapshot",
        inputSchema={
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node name"},
                "vmid": {"type": "integer", "description": "VM ID"},
                "snapname": {"type": "string", "description": "Snapshot name"},
            },
            "required": ["node", "vmid", "snapname"],
        },
    ),
    Tool(
        name="get_cluster_status",
        description="Get overall cluster status and resources",
        inputSchema={"type": "object", "properties": {}},
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    try:
        if name == "list_nodes":
            result = await proxmox.get("/nodes")

        elif name == "get_node_status":
            result = await proxmox.get(f"/nodes/{arguments['node']}/status")

        elif name == "list_vms":
            if "node" in arguments and arguments["node"]:
                result = await proxmox.get(f"/nodes/{arguments['node']}/qemu")
            else:
                # Get all nodes and collect VMs from each
                nodes_result = await proxmox.get("/nodes")
                all_vms = []
                for node in nodes_result["data"]:
                    vms = await proxmox.get(f"/nodes/{node['node']}/qemu")
                    for vm in vms["data"]:
                        vm["node"] = node["node"]
                        all_vms.append(vm)
                result = {"data": all_vms}

        elif name == "get_vm_config":
            result = await proxmox.get(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/config"
            )

        elif name == "get_vm_status":
            result = await proxmox.get(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/status/current"
            )

        elif name == "start_vm":
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/status/start"
            )

        elif name == "stop_vm":
            data = {}
            if "timeout" in arguments:
                data["timeout"] = arguments["timeout"]
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/status/stop",
                data,
            )

        elif name == "shutdown_vm":
            data = {}
            if "timeout" in arguments:
                data["timeout"] = arguments["timeout"]
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/status/shutdown",
                data,
            )

        elif name == "reboot_vm":
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/status/reboot"
            )

        elif name == "list_containers":
            result = await proxmox.get(f"/nodes/{arguments['node']}/lxc")

        elif name == "get_container_status":
            result = await proxmox.get(
                f"/nodes/{arguments['node']}/lxc/{arguments['vmid']}/status/current"
            )

        elif name == "start_container":
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/lxc/{arguments['vmid']}/status/start"
            )

        elif name == "stop_container":
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/lxc/{arguments['vmid']}/status/stop"
            )

        elif name == "list_storage":
            if "node" in arguments and arguments["node"]:
                result = await proxmox.get(f"/nodes/{arguments['node']}/storage")
            else:
                result = await proxmox.get("/storage")

        elif name == "get_storage_status":
            result = await proxmox.get(
                f"/nodes/{arguments['node']}/storage/{arguments['storage']}/status"
            )

        elif name == "list_tasks":
            params = {}
            if "limit" in arguments:
                params["limit"] = arguments["limit"]

            if "node" in arguments and arguments["node"]:
                result = await proxmox.get(
                    f"/nodes/{arguments['node']}/tasks", params
                )
            else:
                result = await proxmox.get("/cluster/tasks", params)

        elif name == "get_task_status":
            result = await proxmox.get(
                f"/nodes/{arguments['node']}/tasks/{arguments['upid']}/status"
            )

        elif name == "create_vm_snapshot":
            data = {"snapname": arguments["snapname"]}
            if "description" in arguments:
                data["description"] = arguments["description"]
            result = await proxmox.post(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/snapshot",
                data,
            )

        elif name == "list_vm_snapshots":
            result = await proxmox.get(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/snapshot"
            )

        elif name == "delete_vm_snapshot":
            result = await proxmox.delete(
                f"/nodes/{arguments['node']}/qemu/{arguments['vmid']}/snapshot/{arguments['snapname']}"
            )

        elif name == "get_cluster_status":
            result = await proxmox.get("/cluster/resources")

        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Main entry point"""
    # Authenticate with Proxmox
    await proxmox.authenticate()

    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
