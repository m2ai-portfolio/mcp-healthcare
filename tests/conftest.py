"""Shared pytest fixtures for MCP Healthcare tests."""

import os
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_env(temp_data_dir, monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("MCP_DATA_DIR", str(temp_data_dir))
    monkeypatch.setenv("MCP_DB_NAME", "test_mcp_hc.sqlite")
    monkeypatch.setenv("MCP_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MCP_AUDIT_ENABLE", "true")

    # Clear any cached settings
    import mcp_healthcare.config
    mcp_healthcare.config._settings = None

    yield temp_data_dir

    # Clear settings again after test
    mcp_healthcare.config._settings = None


@pytest.fixture
def db_manager(test_env):
    """Create a test database manager."""
    from mcp_healthcare.db import DatabaseManager

    db_manager = DatabaseManager()
    db_manager.initialize_schema()

    yield db_manager

    db_manager.close()
