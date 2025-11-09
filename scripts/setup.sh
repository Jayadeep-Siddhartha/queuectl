#!/bin/bash
# QueueCTL Automated Setup Script
# This script automates the complete installation and verification

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "=========================================="
echo "QueueCTL Setup Script"
echo "=========================================="
echo -e "${NC}"

# Function to print step
step() {
    echo -e "\n${GREEN}▶ $1${NC}"
}

# Function to print error
error() {
    echo -e "${RED}✗ Error: $1${NC}"
    exit 1
}

# Function to print success
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Check prerequisites
step "Checking prerequisites..."

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    success "Python found: $PYTHON_VERSION"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version)
    success "Python found: $PYTHON_VERSION"
    PYTHON_CMD="python"
else
    error "Python not found. Please install Python 3.7 or higher."
fi

# Check pip
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
    success "pip3 found"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
    success "pip found"
else
    error "pip not found. Please install pip."
fi

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    error "setup.py not found. Please run this script from the queuectl project root directory."
fi

success "All prerequisites met"

# Create virtual environment
step "Creating virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists. Skipping creation.${NC}"
else
    $PYTHON_CMD -m venv venv
    success "Virtual environment created"
fi

# Activate virtual environment
step "Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    success "Virtual environment activated (Linux/macOS)"
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
    success "Virtual environment activated (Windows)"
else
    error "Could not find activation script"
fi

# Upgrade pip
step "Upgrading pip..."
$PIP_CMD install --upgrade pip > /dev/null 2>&1
success "pip upgraded"

# Install dependencies
step "Installing dependencies..."
$PIP_CMD install -r requirements.txt
success "Dependencies installed"

# Install queuectl
step "Installing queuectl..."
$PIP_CMD install -e .
success "queuectl installed in development mode"

# Verify installation
step "Verifying installation..."
if command -v queuectl &> /dev/null; then
    VERSION=$(queuectl --version)
    success "queuectl is installed: $VERSION"
else
    error "queuectl command not found after installation"
fi

# Run quick test
step "Running quick test..."
TEST_OUTPUT=$(queuectl enqueue '{"id":"test-install","command":"echo Installation Test"}' 2>&1)
if echo "$TEST_OUTPUT" | grep -q "Job enqueued successfully"; then
    success "Test job enqueued successfully"
else
    error "Failed to enqueue test job"
fi

# Clean up test
rm -f queuectl.db queuectl_config.json

# Make scripts executable
step "Making scripts executable..."
chmod +x scripts/demo.sh 2>/dev/null || true
chmod +x scripts/setup.sh 2>/dev/null || true
success "Scripts are executable"

# Print success message
echo ""
echo -e "${GREEN}=========================================="
echo "✓ Installation Complete!"
echo "==========================================${NC}"
echo ""
echo "QueueCTL is now installed and ready to use!"
echo ""
echo -e "${BLUE}Quick Start:${NC}"
echo "  1. Run the demo:"
echo "     ./scripts/demo.sh"
echo ""
echo "  2. Or try these commands:"
echo "     queuectl enqueue '{\"id\":\"hello\",\"command\":\"echo Hello\"}'"
echo "     queuectl worker start"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  queuectl --help         # Show all commands"
echo "  queuectl status         # Check system status"
echo "  queuectl list           # List all jobs"
echo "  queuectl config show    # Show configuration"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo "  README.md      # Complete documentation"
echo "  INSTALL.md     # Installation guide"
echo "  COMMANDS.md    # Command reference"
echo ""
echo -e "${BLUE}Testing:${NC}"
echo "  python tests/test_queuectl.py    # Run test suite"
echo "  ./scripts/demo.sh                # Run demo"
echo ""
echo -e "${YELLOW}Note: The virtual environment is activated.${NC}"
echo "To deactivate: deactivate"
echo "To reactivate: source venv/bin/activate"
echo ""