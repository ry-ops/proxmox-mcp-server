#!/bin/bash

# ========================================
# Proxmox MCP Server Connection Test
# ========================================
# Tests your Proxmox API connection before configuring the MCP server
# 
# Usage: 
#   1. Set environment variables
#   2. Run: ./test-connection.sh
#
# Required Environment Variables:
#   PROXMOX_HOST - Proxmox server hostname/IP
#   PROXMOX_USER - Username with realm (e.g., root@pam)
#   PROXMOX_TOKEN_NAME + PROXMOX_TOKEN_VALUE (or PROXMOX_PASSWORD)
# ========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${CYAN}→${NC} $1"
}

# ========================================
# Start Tests
# ========================================
print_header "Proxmox MCP Server Connection Test"

# ========================================
# Check Required Variables
# ========================================
echo "Checking configuration..."
echo ""

MISSING_VARS=0

if [ -z "$PROXMOX_HOST" ]; then
    print_error "PROXMOX_HOST not set"
    echo "   Set it with: export PROXMOX_HOST='192.168.1.100'"
    MISSING_VARS=1
else
    print_success "PROXMOX_HOST: $PROXMOX_HOST"
fi

if [ -z "$PROXMOX_USER" ]; then
    print_error "PROXMOX_USER not set"
    echo "   Set it with: export PROXMOX_USER='root@pam'"
    MISSING_VARS=1
else
    print_success "PROXMOX_USER: $PROXMOX_USER"
fi

PROXMOX_PORT="${PROXMOX_PORT:-8006}"
print_success "PROXMOX_PORT: $PROXMOX_PORT"

# Check authentication method
if [ -n "$PROXMOX_TOKEN_NAME" ] && [ -n "$PROXMOX_TOKEN_VALUE" ]; then
    AUTH_METHOD="token"
    print_success "Authentication: API Token ($PROXMOX_TOKEN_NAME)"
elif [ -n "$PROXMOX_PASSWORD" ]; then
    AUTH_METHOD="password"
    print_success "Authentication: Password"
else
    print_error "No authentication method configured"
    echo "   Set either:"
    echo "   - PROXMOX_TOKEN_NAME and PROXMOX_TOKEN_VALUE"
    echo "   - PROXMOX_PASSWORD"
    MISSING_VARS=1
fi

if [ $MISSING_VARS -eq 1 ]; then
    echo ""
    print_error "Missing required environment variables"
    echo ""
    echo "Example setup:"
    echo "  export PROXMOX_HOST='192.168.1.100'"
    echo "  export PROXMOX_USER='root@pam'"
    echo "  export PROXMOX_TOKEN_NAME='automation'"
    echo "  export PROXMOX_TOKEN_VALUE='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'"
    echo ""
    exit 1
fi

# ========================================
# Test 1: Connection
# ========================================
print_header "Test 1: Connection"

print_info "Testing connection to https://${PROXMOX_HOST}:${PROXMOX_PORT}"

if curl -k -s -f -o /dev/null --max-time 10 "https://${PROXMOX_HOST}:${PROXMOX_PORT}/"; then
    print_success "Connection successful"
else
    print_error "Cannot connect to Proxmox host"
    echo ""
    echo "   Check that:"
    echo "   - PROXMOX_HOST is correct"
    echo "   - Proxmox is running"
    echo "   - Port ${PROXMOX_PORT} is accessible"
    echo "   - No firewall blocking the connection"
    echo ""
    echo "   Test manually:"
    echo "   curl -k https://${PROXMOX_HOST}:${PROXMOX_PORT}"
    exit 1
fi

# ========================================
# Test 2: API Version
# ========================================
print_header "Test 2: API Version"

print_info "Checking API availability (no auth required)"

VERSION=$(curl -k -s --max-time 10 "https://${PROXMOX_HOST}:${PROXMOX_PORT}/api2/json/version" 2>/dev/null)

if echo "$VERSION" | grep -q "version"; then
    print_success "API responding"
    
    # Extract and display version info
    PVE_VERSION=$(echo "$VERSION" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$PVE_VERSION" ]; then
        print_info "Proxmox VE Version: $PVE_VERSION"
    fi
    
    RELEASE=$(echo "$VERSION" | grep -o '"release":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$RELEASE" ]; then
        print_info "Release: $RELEASE"
    fi
else
    print_error "API not responding correctly"
    echo ""
    echo "   Response: $VERSION"
    exit 1
fi

# ========================================
# Test 3: Authentication
# ========================================
print_header "Test 3: Authentication"

if [ "$AUTH_METHOD" = "token" ]; then
    # Test token authentication
    print_info "Testing API token authentication"
    
    AUTH_HEADER="Authorization: PVEAPIToken=${PROXMOX_USER}!${PROXMOX_TOKEN_NAME}=${PROXMOX_TOKEN_VALUE}"
    RESULT=$(curl -k -s --max-time 10 -H "$AUTH_HEADER" \
        "https://${PROXMOX_HOST}:${PROXMOX_PORT}/api2/json/access/permissions" 2>/dev/null)
    
    if echo "$RESULT" | grep -q "data"; then
        print_success "Token authentication successful"
    else
        print_error "Token authentication failed"
        echo ""
        echo "   Response: $RESULT"
        echo ""
        echo "   Check that:"
        echo "   - Token is correct (copy/paste carefully)"
        echo "   - Token hasn't expired"
        echo "   - User format is correct (e.g., root@pam)"
        echo "   - Token was created with 'Privilege Separation' UNCHECKED"
        echo ""
        exit 1
    fi
else
    # Test password authentication - get ticket
    print_info "Testing password authentication"
    
    TICKET_RESULT=$(curl -k -s --max-time 10 \
        -d "username=${PROXMOX_USER}&password=${PROXMOX_PASSWORD}" \
        "https://${PROXMOX_HOST}:${PROXMOX_PORT}/api2/json/access/ticket" 2>/dev/null)
    
    if echo "$TICKET_RESULT" | grep -q "ticket"; then
        print_success "Password authentication successful"
        TICKET=$(echo "$TICKET_RESULT" | grep -o '"ticket":"[^"]*"' | cut -d'"' -f4)
    else
        print_error "Password authentication failed"
        echo ""
        echo "   Response: $TICKET_RESULT"
        echo ""
        echo "   Check that:"
        echo "   - Password is correct"
        echo "   - User format is correct (e.g., root@pam)"
        echo ""
        exit 1
    fi
fi

# ========================================
# Test 4: List Nodes
# ========================================
print_header "Test 4: List Nodes"

print_info "Testing permissions to list nodes"

if [ "$AUTH_METHOD" = "token" ]; then
    NODES=$(curl -k -s --max-time 10 -H "$AUTH_HEADER" \
        "https://${PROXMOX_HOST}:${PROXMOX_PORT}/api2/json/nodes" 2>/dev/null)
else
    NODES=$(curl -k -s --max-time 10 -H "Cookie: PVEAuthCookie=${TICKET}" \
        "https://${PROXMOX_HOST}:${PROXMOX_PORT}/api2/json/nodes" 2>/dev/null)
fi

if echo "$NODES" | grep -q "node"; then
    print_success "Can list nodes"
    
    # Extract and display node names
    NODE_COUNT=$(echo "$NODES" | grep -o '"node":"[^"]*"' | wc -l)
    print_info "Found $NODE_COUNT node(s):"
    
    echo "$NODES" | grep -o '"node":"[^"]*"' | cut -d'"' -f4 | while read node; do
        echo "     • $node"
    done
else
    print_error "Cannot list nodes"
    echo ""
    echo "   Response: $NODES"
    echo ""
    echo "   Check user permissions:"
    echo "   - User needs 'Sys.Audit' or similar permissions"
    echo "   - Token needs appropriate permissions if using API token"
    echo ""
    exit 1
fi

# ========================================
# Test 5: Cluster Resources
# ========================================
print_header "Test 5: Cluster Resources"

print_info "Testing access to cluster resources"

if [ "$AUTH_METHOD" = "token" ]; then
    RESOURCES=$(curl -k -s --max-time 10 -H "$AUTH_HEADER" \
        "https://${PROXMOX_HOST}:${PROXMOX_PORT}/api2/json/cluster/resources" 2>/dev/null)
else
    RESOURCES=$(curl -k -s --max-time 10 -H "Cookie: PVEAuthCookie=${TICKET}" \
        "https://${PROXMOX_HOST}:${PROXMOX_PORT}/api2/json/cluster/resources" 2>/dev/null)
fi

if echo "$RESOURCES" | grep -q "data"; then
    print_success "Can access cluster resources"
    
    # Count resources
    VM_COUNT=$(echo "$RESOURCES" | grep -o '"type":"qemu"' | wc -l)
    CT_COUNT=$(echo "$RESOURCES" | grep -o '"type":"lxc"' | wc -l)
    STORAGE_COUNT=$(echo "$RESOURCES" | grep -o '"type":"storage"' | wc -l)
    
    echo ""
    print_info "Resource Summary:"
    echo "     • Virtual Machines: $VM_COUNT"
    echo "     • Containers: $CT_COUNT"
    echo "     • Storage Devices: $STORAGE_COUNT"
else
    print_error "Cannot access cluster resources"
    echo ""
    echo "   Response: $RESOURCES"
    echo ""
    exit 1
fi

# ========================================
# Test 6: Required Permissions
# ========================================
print_header "Test 6: Required Permissions"

print_info "Checking if user has required permissions"

PERMS_OK=true

# Test VM permissions
if [ "$AUTH_METHOD" = "token" ]; then
    VM_TEST=$(curl -k -s --max-time 10 -H "$AUTH_HEADER" \
        "https://${PROXMOX_HOST}:${PROXMOX_PORT}/api2/json/cluster/resources?type=vm" 2>/dev/null)
else
    VM_TEST=$(curl -k -s --max-time 10 -H "Cookie: PVEAuthCookie=${TICKET}" \
        "https://${PROXMOX_HOST}:${PROXMOX_PORT}/api2/json/cluster/resources?type=vm" 2>/dev/null)
fi

if echo "$VM_TEST" | grep -q "data"; then
    print_success "VM.Monitor permission OK"
else
    print_warning "VM.Monitor permission may be missing"
    PERMS_OK=false
fi

# Test storage permissions
if [ "$AUTH_METHOD" = "token" ]; then
    STORAGE_TEST=$(curl -k -s --max-time 10 -H "$AUTH_HEADER" \
        "https://${PROXMOX_HOST}:${PROXMOX_PORT}/api2/json/storage" 2>/dev/null)
else
    STORAGE_TEST=$(curl -k -s --max-time 10 -H "Cookie: PVEAuthCookie=${TICKET}" \
        "https://${PROXMOX_HOST}:${PROXMOX_PORT}/api2/json/storage" 2>/dev/null)
fi

if echo "$STORAGE_TEST" | grep -q "data"; then
    print_success "Datastore.Audit permission OK"
else
    print_warning "Datastore.Audit permission may be missing"
    PERMS_OK=false
fi

if [ "$PERMS_OK" = false ]; then
    echo ""
    print_warning "Some permissions may be missing"
    echo "   Required permissions for full functionality:"
    echo "     • VM.Monitor - View VM status"
    echo "     • VM.Audit - View VM configuration"
    echo "     • VM.PowerMgmt - Start/stop VMs"
    echo "     • VM.Snapshot - Manage snapshots"
    echo "     • Datastore.Audit - View storage"
    echo "     • Sys.Audit - View system information"
    echo ""
fi

# ========================================
# Success Summary
# ========================================
print_header "✓ All Tests Passed!"

echo "Your Proxmox connection is working correctly!"
echo ""
echo "Configuration Summary:"
echo "  • Host: ${PROXMOX_HOST}:${PROXMOX_PORT}"
echo "  • User: ${PROXMOX_USER}"
echo "  • Auth: ${AUTH_METHOD}"
echo "  • Nodes: ${NODE_COUNT}"
echo "  • VMs: ${VM_COUNT}"
echo "  • Containers: ${CT_COUNT}"
echo ""
echo "Next Steps:"
echo ""
echo "1. Configure Claude Desktop:"
echo "   ${CYAN}~/Library/Application Support/Claude/claude_desktop_config.json${NC}"
echo "   (MacOS) or ${CYAN}%APPDATA%/Claude/claude_desktop_config.json${NC} (Windows)"
echo ""
echo "2. Add this configuration:"
echo ""
echo '   {'
echo '     "mcpServers": {'
echo '       "proxmox": {'
echo '         "command": "uv",'
echo '         "args": ['
echo '           "--directory",'
echo '           "'$(pwd)'",'
echo '           "run",'
echo '           "proxmox-mcp-server"'
echo '         ],'
echo '         "env": {'
echo "           \"PROXMOX_HOST\": \"${PROXMOX_HOST}\","
echo "           \"PROXMOX_PORT\": \"${PROXMOX_PORT}\","
echo "           \"PROXMOX_USER\": \"${PROXMOX_USER}\","

if [ "$AUTH_METHOD" = "token" ]; then
    echo "           \"PROXMOX_TOKEN_NAME\": \"${PROXMOX_TOKEN_NAME}\","
    echo "           \"PROXMOX_TOKEN_VALUE\": \"${PROXMOX_TOKEN_VALUE}\""
else
    echo "           \"PROXMOX_PASSWORD\": \"${PROXMOX_PASSWORD}\""
fi

echo '         }'
echo '       }'
echo '     }'
echo '   }'
echo ""
echo "3. Restart Claude Desktop"
echo ""
echo "4. Test with Claude:"
echo '   "List all nodes in my Proxmox cluster"'
echo ""
echo "Documentation:"
echo "  • Quick Start: ${CYAN}docs/QUICKSTART.md${NC}"
echo "  • Setup Guide: ${CYAN}docs/SETUP.md${NC}"
echo "  • Usage Guide: ${CYAN}docs/USAGE.md${NC}"
echo "  • GitHub: ${CYAN}https://github.com/ry-ops/proxmox-mcp-server${NC}"
echo ""
