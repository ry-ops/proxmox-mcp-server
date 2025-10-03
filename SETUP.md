# Proxmox Setup Guide

Complete guide for setting up Proxmox VE to work with the MCP server, including authentication, permissions, and security best practices.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Authentication Methods](#authentication-methods)
- [Option 1: API Token Setup (Recommended)](#option-1-api-token-setup-recommended)
- [Option 2: Password Setup](#option-2-password-setup)
- [User and Permission Setup](#user-and-permission-setup)
- [Testing Your Setup](#testing-your-setup)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- ✅ Proxmox VE 6.0 or later installed and running
- ✅ Access to Proxmox web interface
- ✅ Root or administrator access to create users/tokens
- ✅ Network connectivity to Proxmox server (port 8006)

## Authentication Methods

The MCP server supports two authentication methods:

| Method | Security | Best For | Revocable | Expires |
|--------|----------|----------|-----------|---------|
| **API Token** | ⭐⭐⭐⭐⭐ | Production | ✅ Yes | Optional |
| **Password** | ⭐⭐⭐ | Testing | ❌ No | Never |

**Recommendation**: Use API tokens in all cases. They're more secure and easier to manage.

---

## Option 1: API Token Setup (Recommended)

### Step 1: Access Proxmox Web Interface

1. Open your browser
2. Navigate to: `https://your-proxmox-host:8006`
3. Log in with your credentials

### Step 2: Navigate to API Tokens

1. Click **Datacenter** in the left sidebar
2. Expand **Permissions**
3. Click **API Tokens**

### Step 3: Create API Token

1. Click the **Add** button
2. Fill in the token details:

   | Field | Value | Notes |
   |-------|-------|-------|
   | **User** | `root@pam` | Or your preferred user |
   | **Token ID** | `automation` | Descriptive name (no spaces) |
   | **Privilege Separation** | ❌ **UNCHECKED** | ⚠️ CRITICAL - Must uncheck! |
   | **Expire** | Leave empty | Or set future date |
   | **Comment** | `MCP Server Token` | Optional description |

3. Click **Add**

### Step 4: Save Token Secret

⚠️ **CRITICAL**: The token secret is shown **only once**!

1. A dialog will appear showing:
   ```
   Token ID: root@pam!automation
   Secret: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

2. **Copy both values immediately**:
   - Token ID: `root@pam!automation`
   - Secret: The long UUID string

3. Store securely (password manager, encrypted file)

### Step 5: Configure Environment Variables

```bash
export PROXMOX_HOST="192.168.1.100"
export PROXMOX_USER="root@pam"
export PROXMOX_TOKEN_NAME="automation"
export PROXMOX_TOKEN_VALUE="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### Verify Token Creation

**Via Web Interface:**
- Go to Datacenter → Permissions → API Tokens
- You should see `root@pam!automation` listed

**Via CLI** (on Proxmox host):
```bash
pveum user token list root@pam
```

---

## Option 2: Password Setup

⚠️ **Less secure** - Use only for testing or when tokens aren't available.

### Using Existing User Password

Simply use your existing user credentials:

```bash
export PROXMOX_HOST="192.168.1.100"
export PROXMOX_USER="root@pam"
export PROXMOX_PASSWORD="your-password"
```

### Security Considerations

- ❌ Password cannot be revoked independently
- ❌ Changing password affects all access
- ❌ No expiration date
- ❌ Harder to rotate regularly

---

## User and Permission Setup

For better security, create a dedicated user instead of using `root`.

### Step 1: Create Dedicated User

**Via Web Interface:**

1. Go to **Datacenter** → **Permissions** → **Users**
2. Click **Add**
3. Fill in details:
   - **User name**: `mcp-api`
   - **Realm**: `Proxmox VE authentication server`
   - **Password**: Create strong password
   - **Email**: (optional)
4. Click **Add**

**Via CLI** (on Proxmox host):
```bash
pveum user add mcp-api@pve --password <strong-password>
```

### Step 2: Create Custom Role

Create a role with minimal required permissions.

**Via Web Interface:**

1. Go to **Datacenter** → **Permissions** → **Roles**
2. Click **Create**
3. Enter role name: `MCPServerRole`
4. Select privileges:

**Required Privileges:**

| Category | Privilege | Purpose |
|----------|-----------|---------|
| **VM** | `VM.Monitor` | View VM status |
| **VM** | `VM.Audit` | View VM configuration |
| **VM** | `VM.PowerMgmt` | Start/stop/reboot VMs |
| **VM** | `VM.Snapshot` | Create/delete snapshots |
| **Datastore** | `Datastore.Audit` | View storage info |
| **System** | `Sys.Audit` | View system info |

**Optional Privileges** (for extended functionality):

| Privilege | Purpose |
|-----------|---------|
| `VM.Config.Disk` | Modify VM disks |
| `VM.Config.Memory` | Modify VM memory |
| `VM.Config.CPU` | Modify VM CPU |
| `VM.Allocate` | Create/delete VMs |
| `VM.Clone` | Clone VMs |
| `Datastore.AllocateSpace` | Allocate storage |
| `Sys.Syslog` | View system logs |

5. Click **Create**

**Via CLI:**
```bash
pveum role add MCPServerRole \
  -privs "VM.Monitor,VM.Audit,VM.PowerMgmt,VM.Snapshot,Datastore.Audit,Sys.Audit"
```

### Step 3: Assign Permissions

**For Full Cluster Access:**

Via Web Interface:
1. Go to **Datacenter** → **Permissions**
2. Click **Add** → **User Permission**
3. **Path**: `/` (root path)
4. **User**: Select `mcp-api@pve`
5. **Role**: Select `MCPServerRole`
6. Click **Add**

Via CLI:
```bash
pveum acl modify / --user mcp-api@pve --role MCPServerRole
```

**For Specific Node:**
```bash
pveum acl modify /nodes/pve1 --user mcp-api@pve --role MCPServerRole
```

**For Specific VMs:**
```bash
pveum acl modify /vms/100 --user mcp-api@pve --role MCPServerRole
pveum acl modify /vms/101 --user mcp-api@pve --role MCPServerRole
```

### Step 4: Create Token for Dedicated User

Follow [Option 1: API Token Setup](#option-1-api-token-setup-recommended) but select `mcp-api@pve` as the user.

---

## Testing Your Setup

### Quick Test with curl

**Test API Token:**
```bash
curl -k -H "Authorization: PVEAPIToken=root@pam!automation=YOUR_TOKEN_SECRET" \
  https://YOUR_HOST:8006/api2/json/nodes
```

**Expected Response:**
```json
{
  "data": [
    {
      "node": "pve1",
      "status": "online",
      ...
    }
  ]
}
```

### Comprehensive Test

Run the connection test script:
```bash
export PROXMOX_HOST="192.168.1.100"
export PROXMOX_USER="root@pam"
export PROXMOX_TOKEN_NAME="automation"
export PROXMOX_TOKEN_VALUE="your-token-secret"

./test-connection.sh
```

You should see:
```
✓ Connection successful
✓ API responding
✓ Token authentication successful
✓ Can list nodes
✓ Can access cluster resources
✓ VM.Monitor permission OK
✓ Datastore.Audit permission OK
✓ All Tests Passed!
```

### Test with pvesh (on Proxmox host)

```bash
# Test as the MCP user
pvesh get /nodes --username mcp-api@pve --password <password>
pvesh get /cluster/resources --username mcp-api@pve --password <password>
```

---

## Security Best Practices

### 1. Use API Tokens

✅ **DO**: Use API tokens for all integrations
- Can be revoked independently
- Can have expiration dates
- Easier to rotate
- No password exposure

❌ **DON'T**: Use passwords for production
- Cannot revoke without changing password
- No expiration
- Harder to audit

### 2. Principle of Least Privilege

Grant only the permissions needed:

**Minimum for read-only monitoring:**
```bash
VM.Monitor, VM.Audit, Datastore.Audit, Sys.Audit
```

**Add for VM control:**
```bash
+ VM.PowerMgmt, VM.Snapshot
```

**Add for VM management:**
```bash
+ VM.Config.*, VM.Allocate
```

### 3. Token Management

**Set Expiration Dates:**
- Production: 1 year
- Development: 90 days
- Testing: 30 days

**Regular Rotation:**
```bash
# Create new token
pveum user token add mcp-api@pve automation-2024 --privsep 0

# Update MCP server config

# Delete old token
pveum user token remove mcp-api@pve automation-2023
```

### 4. Audit and Monitoring

**Review token usage:**
```bash
# On Proxmox host
journalctl -u pveproxy | grep "API token"
tail -f /var/log/pve/tasks/index
```

**Check permissions:**
```bash
pveum acl list
pveum user list --enabled 1 --full
```

### 5. Network Security

**Firewall Rules:**
```bash
# Allow only from specific IP
iptables -A INPUT -p tcp --dport 8006 -s 192.168.1.50 -j ACCEPT
iptables -A INPUT -p tcp --dport 8006 -j DROP
```

**Use VPN:**
- Access Proxmox through VPN only
- Don't expose port 8006 to internet

### 6. SSL/TLS

**Enable SSL Verification in Production:**

1. Install valid SSL certificate on Proxmox
2. Set environment variable:
   ```bash
   export PROXMOX_VERIFY_SSL=true
   ```

**Install Let's Encrypt certificate:**
```bash
# On Proxmox host
pvenode acme account register default mail@example.com
pvenode config set --acme domains=pve.example.com
pvenode acme cert order
```

### 7. Credential Storage

**DO:**
- ✅ Use environment variables
- ✅ Use password managers (1Password, Bitwarden)
- ✅ Use secret management (Vault, AWS Secrets Manager)
- ✅ Encrypt configuration files

**DON'T:**
- ❌ Commit credentials to git
- ❌ Store in plain text files
- ❌ Share credentials via email/chat
- ❌ Hardcode in application

---

## Troubleshooting

### "Authentication failed"

**Problem**: Cannot authenticate with Proxmox

**Check:**
- ✅ Token secret is correct (no spaces, complete UUID)
- ✅ User format includes realm: `root@pam` not just `root`
- ✅ Token hasn't expired
- ✅ "Privilege Separation" was **unchecked**

**Solutions:**
```bash
# Check token exists
pveum user token list root@pam

# Create new token
pveum user token add root@pam automation --privsep 0

# Test manually
curl -k -H "Authorization: PVEAPIToken=root@pam!automation=SECRET" \
  https://YOUR_HOST:8006/api2/json/nodes
```

### "Permission denied"

**Problem**: User lacks required permissions

**Check:**
```bash
# View user permissions
pveum user list root@pam --full

# View ACL
pveum acl list
```

**Solutions:**
```bash
# Add missing permissions
pveum acl modify / --user mcp-api@pve --role MCPServerRole

# Or grant specific privilege
pveum acl modify / --user mcp-api@pve --role PVEAdmin
```

### "Connection refused"

**Problem**: Cannot connect to Proxmox

**Check:**
- ✅ PROXMOX_HOST is correct
- ✅ Proxmox is running: `systemctl status pveproxy`
- ✅ Port 8006 is open
- ✅ No firewall blocking

**Solutions:**
```bash
# Check if pveproxy is running
systemctl status pveproxy

# Restart if needed
systemctl restart pveproxy

# Check firewall
iptables -L -n | grep 8006

# Test locally
curl -k https://localhost:8006/api2/json/version
```

### "SSL certificate verification failed"

**Problem**: SSL errors when `PROXMOX_VERIFY_SSL=true`

**Solutions:**

**Option 1: Disable verification (testing only)**
```bash
export PROXMOX_VERIFY_SSL=false
```

**Option 2: Install valid certificate**
```bash
# On Proxmox host - use Let's Encrypt
pvenode acme account register default mail@example.com
pvenode config set --acme domains=pve.example.com
pvenode acme cert order
systemctl restart pveproxy
```

**Option 3: Install custom certificate**
```bash
# On Proxmox host
cp your-cert.pem /etc/pve/local/pveproxy-ssl.pem
cp your-key.pem /etc/pve/local/pveproxy-ssl.key
systemctl restart pveproxy
```

### "Token shows 'Privilege Separation: Yes'"

**Problem**: Token was created with privilege separation

**Solution**: Recreate token with privilege separation disabled

```bash
# Delete old token
pveum user token remove root@pam automation

# Create new token with --privsep 0
pveum user token add root@pam automation --privsep 0
```

---

## Next Steps

After completing setup:

1. ✅ **Test connection**: Run `./test-connection.sh`
2. ✅ **Configure MCP server**: See [QUICKSTART.md](QUICKSTART.md)
3. ✅ **Set up Claude Desktop**: Follow configuration guide
4. ✅ **Review usage examples**: See [USAGE.md](USAGE.md)
5. ✅ **Implement monitoring**: Set up audit logging

## Additional Resources

- [Proxmox VE API Documentation](https://pve.proxmox.com/wiki/Proxmox_VE_API)
- [Proxmox User Management](https://pve.proxmox.com/wiki/User_Management)
- [Proxmox Permission System](https://pve.proxmox.com/wiki/Proxmox_VE_Permission_System)
- [GitHub Repository](https://github.com/ry-ops/proxmox-mcp-server)

---

**Questions?** Open an issue on [GitHub](https://github.com/ry-ops/proxmox-mcp-server/issues)

You have two options:

1. **API Token** (Recommended) - More secure, can be revoked independently
2. **Password** - Simpler setup, uses existing user password

This guide covers both methods.

## Step 2: Create a Dedicated User (Optional but Recommended)

For better security, create a dedicated user for the MCP server instead of using root.

### Using Web Interface

1. Log into Proxmox web interface
2. Navigate to **Datacenter** → **Permissions** → **Users**
3. Click **Add** button
4. Fill in the details:
   - **User name**: `mcp-api` (or your preferred name)
   - **Realm**: `Proxmox VE authentication server`
   - **Password**: Create a strong password
   - **Email**: (optional)
5. Click **Add**

### Using Command Line (SSH)

```bash
pveum user add mcp-api@pve --password <password>
```

## Step 3: Create Custom Role with Required Permissions

Create a role with the minimum required permissions.

### Using Web Interface

1. Navigate to **Datacenter** → **Permissions** → **Roles**
2. Click **Create** button
3. Enter role name: `MCPServerRole`
4. Select the following privileges:

**VM Permissions:**
- `VM.Monitor` - View VM status and configuration
- `VM.Audit` - View VM configuration
- `VM.PowerMgmt` - Start, stop, shutdown VMs
- `VM.Snapshot` - Create, delete snapshots
- `VM.Snapshot.Rollback` - Rollback to snapshots (optional)

**Datastore Permissions:**
- `Datastore.Audit` - View storage information
- `Datastore.AllocateSpace` - Allocate disk space (if creating VMs)

**System Permissions:**
- `Sys.Audit` - View system information
- `Sys.Syslog` - View system logs (optional)

**Pool Permissions (if using pools):**
- `Pool.Audit` - View pool information

5. Click **Create**

### Using Command Line

```bash
pveum role add MCPServerRole \
  -privs "VM.Monitor,VM.Audit,VM.PowerMgmt,VM.Snapshot,Datastore.Audit,Sys.Audit"
```

## Step 4: Assign Permissions

Assign the role to the user on the appropriate path.

### For Full Cluster Access

Using Web Interface:
1. Navigate to **Datacenter** → **Permissions**
2. Click **Add** → **User Permission**
3. **Path**: `/` (root)
4. **User**: Select `mcp-api@pve`
5. **Role**: Select `MCPServerRole`
6. Click **Add**

Using Command Line:
```bash
pveum acl modify / --user mcp-api@pve --role MCPServerRole
```

### For Specific Node Access

Using Command Line:
```bash
# For a specific node
pveum acl modify /nodes/pve1 --user mcp-api@pve --role MCPServerRole

# For specific VMs
pveum acl modify /vms/100 --user mcp-api@pve --role MCPServerRole
```

## Step 5A: Create API Token (Recommended)

### Using Web Interface

1. Navigate to **Datacenter** → **Permissions** → **API Tokens**
2. Select your user (`mcp-api@pve` or `root@pam`)
3. Click **Add** button
4. Fill in:
   - **Token ID**: `automation` (or your preferred name)
   - **Privilege Separation**: Leave **unchecked** to inherit user permissions
   - **Expiration**: Set if desired (or leave empty for no expiration)
5. Click **Add**
6. **IMPORTANT**: Copy the displayed token secret immediately! You won't be able to see it again.

The token identifier will be: `mcp-api@pve!automation`

### Using Command Line

```bash
# Create token (returns the secret value)
pveum user token add mcp-api@pve automation --privsep 0

# Output will be something like:
# ┌──────────────┬──────────────────────────────────────┐
# │ key          │ value                                │
# ╞══════════════╪══════════════════════════════════════╡
# │ full-tokenid │ mcp-api@pve!automation               │
# ├──────────────┼──────────────────────────────────────┤
# │ info         │ {"privsep":"0"}                      │
# ├──────────────┼──────────────────────────────────────┤
# │ value        │ xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx │
# └──────────────┴──────────────────────────────────────┘
```

Save the token value securely!

### Configure Environment

Using API token:
```bash
export PROXMOX_HOST="192.168.1.100"
export PROXMOX_USER="mcp-api@pve"
export PROXMOX_TOKEN_NAME="automation"
export PROXMOX_TOKEN_VALUE="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

## Step 5B: Use Password Authentication (Alternative)

If you prefer password authentication (less secure):

```bash
export PROXMOX_HOST="192.168.1.100"
export PROXMOX_USER="mcp-api@pve"
export PROXMOX_PASSWORD="your-secure-password"
```

## Step 6: Test API Access

Test your authentication using curl or pvesh.

### Test with API Token

```bash
curl -k -H "Authorization: PVEAPIToken=mcp-api@pve!automation=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" \
  https://192.168.1.100:8006/api2/json/nodes
```

### Test with Password

```bash
# Get ticket
curl -k -d "username=mcp-api@pve&password=your-password" \
  https://192.168.1.100:8006/api2/json/access/ticket

# Use ticket (replace TICKET with actual ticket value)
curl -k -H "Cookie: PVEAuthCookie=TICKET" \
  https://192.168.1.100:8006/api2/json/nodes
```

### Test with pvesh (on Proxmox host)

```bash
# As the user (if you have shell access)
pvesh get /nodes
pvesh get /cluster/resources
```

## Step 7: Configure Claude Desktop

Edit your Claude Desktop configuration file:

**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

### Configuration with API Token

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "node",
      "args": ["/absolute/path/to/proxmox-mcp-server/build/index.js"],
      "env": {
        "PROXMOX_HOST": "192.168.1.100",
        "PROXMOX_USER": "mcp-api@pve",
        "PROXMOX_TOKEN_NAME": "automation",
        "PROXMOX_TOKEN_VALUE": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "PROXMOX_VERIFY_SSL": "false"
      }
    }
  }
}
```

### Configuration with Password

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "node",
      "args": ["/absolute/path/to/proxmox-mcp-server/build/index.js"],
      "env": {
        "PROXMOX_HOST": "192.168.1.100",
        "PROXMOX_USER": "mcp-api@pve",
        "PROXMOX_PASSWORD": "your-secure-password",
        "PROXMOX_VERIFY_SSL": "false"
      }
    }
  }
}
```

## Step 8: Restart Claude Desktop

After updating the configuration:
1. Quit Claude Desktop completely
2. Restart Claude Desktop
3. Open a new conversation
4. The Proxmox tools should now be available

## Verification

Test the integration by asking Claude:

```
List all nodes in my Proxmox cluster
```

If successful, Claude will use the `list_nodes` tool and show your nodes.

## Security Best Practices

### 1. Use Dedicated User

Don't use root@pam for the MCP server. Create a dedicated user with limited permissions.

### 2. Principle of Least Privilege

Only grant permissions that are actually needed. Review the permission list and remove any that aren't necessary for your use case.

### 3. API Token over Password

API tokens are more secure because:
- They can be revoked without changing the user password
- They can have expiration dates
- They can be easily rotated
- Compromise doesn't expose the user password

### 4. Token Rotation

Regularly rotate API tokens:
1. Create a new token
2. Update configuration
3. Test the new token
4. Delete the old token

### 5. Enable SSL Verification

Once you have valid SSL certificates:
```bash
export PROXMOX_VERIFY_SSL="true"
```

### 6. Network Restrictions

Consider restricting API access by IP address using firewall rules:

```bash
# On Proxmox host
# Allow only from specific IP
iptables -A INPUT -p tcp --dport 8006 -s 192.168.1.50 -j ACCEPT
iptables -A INPUT -p tcp --dport 8006 -j DROP
```

### 7. Audit Logs

Regularly review API access in Proxmox logs:
```bash
# On Proxmox host
tail -f /var/log/pve/tasks/index
journalctl -u pveproxy
```

### 8. Token Expiration

Set expiration dates on tokens to force regular rotation:
```bash
# Set token to expire in 90 days
pveum user token add mcp-api@pve automation --privsep 0 --expire $(date -d "+90 days" +%s)
```

## Troubleshooting Setup

### "Authentication failed"

**Check:**
- Username format includes realm (e.g., `mcp-api@pve` not just `mcp-api`)
- Token secret is correct (check for copy/paste errors)
- Password is correct
- User account is not disabled

**Solution:**
```bash
# Check if user exists
pveum user list

# Check token
pveum user token list mcp-api@pve

# Reset password if needed
pveum passwd mcp-api@pve
```

### "Permission denied"

**Check:**
- User has required permissions on the path
- Role includes necessary privileges
- Privilege separation is disabled on token (--privsep 0)

**Solution:**
```bash
# List user permissions
pveum acl list

# Check specific user permissions
pveum user list --enabled 1 --full

# Add missing permissions
pveum acl modify / --user mcp-api@pve --role MCPServerRole
```

### "Connection refused"

**Check:**
- Proxmox web interface is accessible
- Port 8006 is open
- No firewall blocking the connection

**Solution:**
```bash
# Check if pveproxy is running
systemctl status pveproxy

# Check firewall
iptables -L -n | grep 8006

# Test locally on Proxmox host
curl -k https://localhost:8006/api2/json/version
```

### "SSL Certificate Verification Failed"

If you see SSL errors but want to use the server:

**Temporary:**
```bash
export PROXMOX_VERIFY_SSL="false"
```

**Permanent Solution:**
Install valid SSL certificates on Proxmox:
```bash
# Copy your certificates to Proxmox
scp cert.pem root@proxmox:/etc/pve/local/pveproxy-ssl.pem
scp key.pem root@proxmox:/etc/pve/local/pveproxy-ssl.key

# Restart pveproxy
systemctl restart pveproxy
```

## Advanced Configuration

### Multiple Proxmox Servers

You can configure multiple Proxmox servers:

```json
{
  "mcpServers": {
    "proxmox-prod": {
      "command": "node",
      "args": ["/path/to/proxmox-mcp-server/build/index.js"],
      "env": {
        "PROXMOX_HOST": "proxmox-prod.example.com",
        "PROXMOX_USER": "mcp-api@pve",
        "PROXMOX_TOKEN_NAME": "automation",
        "PROXMOX_TOKEN_VALUE": "token-value-1"
      }
    },
    "proxmox-dev": {
      "command": "node",
      "args": ["/path/to/proxmox-mcp-server/build/index.js"],
      "env": {
        "PROXMOX_HOST": "proxmox-dev.example.com",
        "PROXMOX_USER": "mcp-api@pve",
        "PROXMOX_TOKEN_NAME": "automation",
        "PROXMOX_TOKEN_VALUE": "token-value-2"
      }
    }
  }
}
```

### Using Different Realms

Proxmox supports multiple authentication realms:

- `pam` - Linux PAM authentication
- `pve` - Proxmox VE authentication server
- `ldap` - LDAP/Active Directory
- `ad` - Active Directory

Example for AD:
```bash
export PROXMOX_USER="john.doe@DOMAIN.COM"
```

## Next Steps

After setup:
1. Read the [Usage Guide](USAGE.md) for examples
2. Test basic operations with Claude
3. Explore available tools
4. Set up monitoring and alerting
5. Create backup procedures using snapshots

## Getting Help

- Proxmox Documentation: https://pve.proxmox.com/pve-docs/
- Proxmox API: https://pve.proxmox.com/pve-docs/api-viewer/
- Proxmox Forum: https://forum.proxmox.com/
- MCP Documentation: https://modelcontextprotocol.io/
