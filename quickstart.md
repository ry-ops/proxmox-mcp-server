# Quick Start Guide

Get up and running with the Proxmox MCP Server in 5 minutes!

## 1. Install Dependencies

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

## 2. Create Project Structure

```bash
# Create the Python package structure
mkdir -p src/proxmox_mcp_server
touch src/proxmox_mcp_server/__init__.py
# Move server.py to src/proxmox_mcp_server/server.py
```

## 3. Create API Token in Proxmox

1. Open Proxmox web interface
2. Go to **Datacenter** → **Permissions** → **API Tokens**
3. Click **Add**
4. Select user (e.g., `root@pam`)
5. Enter Token ID: `automation`
6. Uncheck "Privilege Separation"
7. Click **Add**
8. **Copy the token secret** (you won't see it again!)

## 4. Configure Claude Desktop

Edit config file:
- **MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

Add this configuration (replace values with yours):

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "uv",
      "args": [
        "--directory",
        "/FULL/PATH/TO/proxmox-mcp-server",
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

**Important**: Use the absolute path to your project!

## 5. Restart Claude Desktop

Completely quit and restart Claude Desktop.

## 6. Test It!

Open a new conversation in Claude and try:

```
List all nodes in my Proxmox cluster
```

```
Show me all VMs
```

```
What's the status of VM 100 on pve1?
```

That's it! 🎉

## Next Steps

- Read [SETUP.md](SETUP.md) for detailed setup and security best practices
- Read [USAGE.md](USAGE.md) for usage examples
- Check [README.md](README.md) for complete documentation

## Common Issues

### ❌ "Authentication failed"

**Check:**
- Token value is correct (no extra spaces)
- User format includes realm: `root@pam` not just `root`
- Token hasn't expired

**Fix:**
Create a new token and update your config.

### ❌ "Connection refused"

**Check:**
- `PROXMOX_HOST` is correct
- Proxmox is running (try accessing web interface)
- Port 8006 is accessible

**Fix:**
Test with: `curl -k https://YOUR_HOST:8006/api2/json/version`

### ❌ "Tools not showing in Claude"

**Check:**
- Path in config is absolute, not relative
- Config file is valid JSON (use a JSON validator)
- You restarted Claude Desktop

**Fix:**
1. Validate JSON config
2. Use full absolute path
3. Quit Claude completely (not just close window)
4. Start Claude again

### ❌ "Permission denied"

**Check:**
- User/token has required permissions
- "Privilege Separation" was unchecked when creating token

**Fix:**
Create new token with "Privilege Separation" unchecked, or assign proper permissions.

## Test Authentication

Before configuring Claude, test your credentials:

```bash
# Set variables
export PROXMOX_HOST="192.168.1.100"
export PROXMOX_USER="root@pam"
export PROXMOX_TOKEN_NAME="automation"
export PROXMOX_TOKEN_VALUE="your-token-here"

# Test with curl
curl -k -H "Authorization: PVEAPIToken=${PROXMOX_USER}!${PROXMOX_TOKEN_NAME}=${PROXMOX_TOKEN_VALUE}" \
  https://${PROXMOX_HOST}:8006/api2/json/nodes
```

If you see JSON output with your nodes, authentication is working!

## Alternative: Password Authentication

If you prefer password authentication:

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "uv",
      "args": [
        "--directory",
        "/FULL/PATH/TO/proxmox-mcp-server",
        "run",
        "proxmox-mcp-server"
      ],
      "env": {
        "PROXMOX_HOST": "192.168.1.100",
        "PROXMOX_USER": "root@pam",
        "PROXMOX_PASSWORD": "your-password"
      }
    }
  }
}
```

⚠️ **Note**: API tokens are more secure than passwords!

## Verify Installation

Once Claude is restarted, in the conversation you should see Proxmox tools available. Try these commands:

1. **List nodes**: "Show me all Proxmox nodes"
2. **List VMs**: "List all virtual machines"
3. **Check status**: "What's the cluster status?"

If these work, you're all set! ✅

## Getting Help

- **Detailed Setup**: See [SETUP.md](SETUP.md)
- **Usage Examples**: See [USAGE.md](USAGE.md)
- **Full Documentation**: See [README.md](README.md)
- **Proxmox API Docs**: https://pve.proxmox.com/pve-docs/api-viewer/

## Security Reminder

⚠️ Never commit credentials to git!

The `.gitignore` file excludes `.env` files, but be careful with:
- Claude Desktop config (contains credentials)
- Scripts or notes with credentials
- Screenshots showing tokens

For production use, read the security section in [SETUP.md](SETUP.md).
