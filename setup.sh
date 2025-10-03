#!/bin/bash

# ========================================
# Proxmox MCP Server Setup Script
# ========================================
# Automates the initial setup of the project
# 
# What this script does:
# - Checks for and installs uv
# - Creates project directory structure
# - Installs dependencies
# - Sets up configuration files
# - Makes scripts executable
# - Provides next steps
#
# Usage: ./setup.sh
# ========================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
    echo -e "${BLUE}ℹ${NC} $1"
}

# ========================================
# Start Setup
# ========================================
print_header "Proxmox MCP Server Setup"

echo "This script will set up your Proxmox MCP Server environment."
echo ""

# ========================================
# Check Python Version
# ========================================
print_info "Checking Python version..."

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        print_success "Python $PYTHON_VERSION found"
    else
        print_error "Python 3.10 or higher is required (found $PYTHON_VERSION)"
        exit 1
    fi
else
    print_error "Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

# ========================================
# Check/Install uv
# ========================================
print_info "Checking for uv package manager..."

if ! command -v uv &> /dev/null; then
    print_warning "uv is not installed"
    echo ""
    echo "Installing uv..."
    
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        print_success "uv installed successfully"
        echo ""
        print_warning "Please restart your shell and run this script again"
        print_info "Run: source ~/.bashrc  (or ~/.zshrc)"
        exit 0
    else
        print_error "Failed to install uv"
        print_info "Visit: https://github.com/astral-sh/uv"
        exit 1
    fi
else
    UV_VERSION=$(uv --version 2>&1 | awk '{print $2}')
    print_success "uv $UV_VERSION found"
fi

echo ""

# ========================================
# Create Directory Structure
# ========================================
print_header "Creating Directory Structure"

print_info "Creating project directories..."

# Create main directories
mkdir -p src/proxmox_mcp_server
mkdir -p docs
mkdir -p .github/ISSUE_TEMPLATE
mkdir -p .github/workflows

print_success "Directories created"

# Create __init__.py if it doesn't exist or is empty
print_info "Setting up Python package..."

if [ ! -f "src/proxmox_mcp_server/__init__.py" ] || [ ! -s "src/proxmox_mcp_server/__init__.py" ]; then
    cat > src/proxmox_mcp_server/__init__.py << 'EOF'
"""
Proxmox MCP Server
==================

A Model Context Protocol (MCP) server for managing Proxmox Virtual Environment.

GitHub: https://github.com/ry-ops/proxmox-mcp-server
Documentation: https://github.com/ry-ops/proxmox-mcp-server#readme

Author: ry-ops
License: MIT
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
EOF
    print_success "__init__.py created"
else
    print_success "__init__.py already exists"
fi

# Check if server.py exists
if [ ! -f "src/proxmox_mcp_server/server.py" ]; then
    print_warning "server.py not found in src/proxmox_mcp_server/"
    print_info "Please add server.py to src/proxmox_mcp_server/ directory"
fi

echo ""

# ========================================
# Create .env.example
# ========================================
print_header "Setting Up Configuration"

if [ ! -f ".env.example" ]; then
    print_info "Creating .env.example..."
    
    cat > .env.example << 'EOF'
# Proxmox MCP Server Configuration
# Copy this file to .env and fill in your values

# Required: Proxmox server hostname or IP
PROXMOX_HOST=192.168.1.100

# Required: Username with realm (e.g., root@pam, admin@pve)
PROXMOX_USER=root@pam

# Optional: API port (default: 8006)
PROXMOX_PORT=8006

# Authentication Method 1: API Token (Recommended)
PROXMOX_TOKEN_NAME=automation
PROXMOX_TOKEN_VALUE=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Authentication Method 2: Password (Alternative)
# PROXMOX_PASSWORD=your-secure-password

# Optional: SSL certificate verification (default: false)
PROXMOX_VERIFY_SSL=false
EOF
    print_success ".env.example created"
else
    print_success ".env.example already exists"
fi

echo ""

# ========================================
# Install Dependencies
# ========================================
print_header "Installing Dependencies"

print_info "Running uv sync..."
echo ""

if uv sync; then
    print_success "Dependencies installed successfully"
else
    print_error "Failed to install dependencies"
    exit 1
fi

echo ""

# ========================================
# Make Scripts Executable
# ========================================
print_header "Setting Script Permissions"

if [ -f "test-connection.sh" ]; then
    chmod +x test-connection.sh
    print_success "test-connection.sh is now executable"
fi

if [ -f "setup.sh" ]; then
    chmod +x setup.sh
    print_success "setup.sh is now executable"
fi

echo ""

# ========================================
# Verify Installation
# ========================================
print_header "Verifying Installation"

print_info "Checking package installation..."

if uv run python -c "import proxmox_mcp_server; print(f'Version: {proxmox_mcp_server.__version__}')" 2>/dev/null; then
    print_success "Package installed correctly"
else
    print_warning "Package verification incomplete (this is normal if server.py is not yet added)"
fi

echo ""

# ========================================
# Print Next Steps
# ========================================
print_header "Setup Complete!"

echo "Your Proxmox MCP Server is ready to configure!"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Create an API token in Proxmox:"
echo "   • Open Proxmox web interface"
echo "   • Go to: Datacenter → Permissions → API Tokens"
echo "   • Create a token for your user"
echo "   • ⚠️  UNCHECK 'Privilege Separation'"
echo "   • Copy the token secret"
echo ""
echo "2. Set environment variables:"
echo "   ${GREEN}export PROXMOX_HOST='your-proxmox-host'${NC}"
echo "   ${GREEN}export PROXMOX_USER='root@pam'${NC}"
echo "   ${GREEN}export PROXMOX_TOKEN_NAME='automation'${NC}"
echo "   ${GREEN}export PROXMOX_TOKEN_VALUE='your-token-value'${NC}"
echo ""
echo "3. Test the connection:"
if [ -f "test-connection.sh" ]; then
    echo "   ${GREEN}./test-connection.sh${NC}"
else
    echo "   ${YELLOW}(test-connection.sh not found - add it to test)${NC}"
fi
echo ""
echo "4. Configure Claude Desktop:"
echo "   • MacOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "   • Windows: %APPDATA%/Claude/claude_desktop_config.json"
echo ""
echo "   Add this configuration:"
echo '   {'
echo '     "mcpServers": {'
echo '       "proxmox": {'
echo '         "command": "uv",'
echo "         \"args\": [\"--directory\", \"$(pwd)\", \"run\", \"proxmox-mcp-server\"],"
echo '         "env": {'
echo '           "PROXMOX_HOST": "your-host",'
echo '           "PROXMOX_USER": "root@pam",'
echo '           "PROXMOX_TOKEN_NAME": "automation",'
echo '           "PROXMOX_TOKEN_VALUE": "your-token"'
echo '         }'
echo '       }'
echo '     }'
echo '   }'
echo ""
echo "5. Restart Claude Desktop"
echo ""
echo "6. Test with Claude:"
echo "   'List all nodes in my Proxmox cluster'"
echo ""
echo "📚 Documentation:"
echo "   • Quick Start: docs/QUICKSTART.md"
echo "   • Setup Guide: docs/SETUP.md"
echo "   • Usage Guide: docs/USAGE.md"
echo "   • GitHub: https://github.com/ry-ops/proxmox-mcp-server"
echo ""
print_success "Setup script completed successfully!"
echo ""
