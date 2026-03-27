#!/bin/bash

set -e

echo "MCP-Healthcare: Initializing development environment..."
echo ""

# Determine Python executable
PYTHON_CMD="python3.11"
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD="python3"
fi

if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "Error: Python 3.11+ is required but not found"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "Using Python: $PYTHON_VERSION"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Project directory: $PROJECT_DIR"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "Creating Python virtual environment..."
    $PYTHON_CMD -m venv "$PROJECT_DIR/venv"
    echo "Virtual environment created at: $PROJECT_DIR/venv"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$PROJECT_DIR/venv/bin/activate"
echo ""

# Upgrade pip, setuptools, wheel
echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel
echo ""

# Install dependencies
echo "Installing dependencies..."
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    pip install -r "$PROJECT_DIR/requirements.txt"
    echo "Installed from requirements.txt"
else
    # Install minimal dependencies (no sqlalchemy - using built-in sqlite3)
    pip install click pydantic pydantic-settings pytest
    echo "Installed core dependencies (click, pydantic, pydantic-settings, pytest)"
fi

# Install package in editable mode if pyproject.toml exists
if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    pip install -e "$PROJECT_DIR"
    echo "Installed package in editable mode"
fi
echo ""

# Create data directory
echo "Setting up directories..."
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/logs"
echo "Created: $PROJECT_DIR/data"
echo "Created: $PROJECT_DIR/logs"
echo ""

# Set default environment variables
echo "Setting environment variables..."
export MCP_DATA_DIR="$PROJECT_DIR/data"
export MCP_DB_NAME="mcp_hc.sqlite"
export MCP_LOG_LEVEL="INFO"
export MCP_AUDIT_ENABLE="true"

echo "MCP_DATA_DIR=$MCP_DATA_DIR"
echo "MCP_DB_NAME=$MCP_DB_NAME"
echo "MCP_LOG_LEVEL=$MCP_LOG_LEVEL"
echo "MCP_AUDIT_ENABLE=$MCP_AUDIT_ENABLE"
echo ""

# Run smoke tests
echo "Running smoke tests..."
echo ""

# Test Python import
if command -v python &> /dev/null; then
    python --version
    echo "Python is available"
fi

# Test Click is installed
python -c "import click; print('Click version:', click.__version__)" 2>/dev/null && echo "✓ Click installed" || echo "✗ Click not available"

# Test Pydantic is installed
python -c "import pydantic; print('Pydantic version:', pydantic.__version__)" 2>/dev/null && echo "✓ Pydantic installed" || echo "✗ Pydantic not available"

# Test Pytest is installed
python -c "import pytest; print('Pytest version:', pytest.__version__)" 2>/dev/null && echo "✓ Pytest installed" || echo "✗ Pytest not available"

echo ""
echo "Setup complete!"
echo ""
echo "To activate the virtual environment in future sessions, run:"
echo "  source $PROJECT_DIR/venv/bin/activate"
echo ""
echo "To run tests:"
echo "  pytest"
echo ""
echo "To see help:"
echo "  python -m mcp_healthcare --help"
echo ""
