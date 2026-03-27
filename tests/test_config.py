"""Tests for configuration management."""

import os
import pytest
from pathlib import Path

from mcp_healthcare.config import Settings, get_settings


def test_default_settings():
    """Test that default settings are loaded correctly."""
    settings = Settings()

    assert settings.mcp_data_dir == "./data"
    assert settings.mcp_db_name == "mcp_hc.sqlite"
    assert settings.mcp_log_level == "INFO"
    assert settings.mcp_audit_enable is True


def test_settings_from_env_vars(test_env):
    """Test that settings load from environment variables."""
    settings = get_settings()

    assert "test_mcp_hc.sqlite" in str(settings.db_path)
    assert settings.mcp_log_level == "DEBUG"
    assert settings.mcp_audit_enable is True


def test_data_dir_path_property(test_env):
    """Test that data_dir_path property returns a Path object."""
    settings = get_settings()
    data_dir = settings.data_dir_path

    assert isinstance(data_dir, Path)
    assert data_dir.is_absolute()


def test_db_path_property(test_env):
    """Test that db_path property returns correct path."""
    settings = get_settings()
    db_path = settings.db_path

    assert isinstance(db_path, Path)
    assert db_path.name == "test_mcp_hc.sqlite"
    assert db_path.parent == settings.data_dir_path


def test_ensure_data_dir(test_env):
    """Test that ensure_data_dir creates the directory."""
    settings = get_settings()

    # Directory might not exist yet
    settings.ensure_data_dir()

    # Now it should exist
    assert settings.data_dir_path.exists()
    assert settings.data_dir_path.is_dir()


def test_audit_enable_boolean(monkeypatch):
    """Test that MCP_AUDIT_ENABLE is parsed as boolean."""
    # Clear cached settings
    import mcp_healthcare.config
    mcp_healthcare.config._settings = None

    # Test with string "false"
    monkeypatch.setenv("MCP_AUDIT_ENABLE", "false")
    settings = Settings()
    assert settings.mcp_audit_enable is False

    # Clear and test with string "true"
    mcp_healthcare.config._settings = None
    monkeypatch.setenv("MCP_AUDIT_ENABLE", "true")
    settings = Settings()
    assert settings.mcp_audit_enable is True

    # Clear and test with boolean-ish values
    mcp_healthcare.config._settings = None
    monkeypatch.setenv("MCP_AUDIT_ENABLE", "0")
    settings = Settings()
    assert settings.mcp_audit_enable is False

    mcp_healthcare.config._settings = None
    monkeypatch.setenv("MCP_AUDIT_ENABLE", "1")
    settings = Settings()
    assert settings.mcp_audit_enable is True


def test_get_settings_singleton():
    """Test that get_settings returns the same instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2
