"""Tests for database management."""

import sqlite3
import pytest
from pathlib import Path

from mcp_healthcare.db import DatabaseManager, init_database
from mcp_healthcare.config import get_settings


def test_database_initialization(test_env):
    """Test that database is initialized correctly."""
    db_manager = DatabaseManager()
    db_manager.initialize_schema()

    # Check that database file exists
    settings = get_settings()
    assert settings.db_path.exists()

    # Check that connection works
    conn = db_manager.connect()
    assert isinstance(conn, sqlite3.Connection)

    db_manager.close()


def test_audit_log_table_exists(db_manager):
    """Test that audit_log table is created."""
    conn = db_manager.connect()

    # Query for the audit_log table
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'"
    )
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == "audit_log"


def test_audit_log_table_schema(db_manager):
    """Test that audit_log table has correct schema."""
    conn = db_manager.connect()

    # Get table info
    cursor = conn.execute("PRAGMA table_info(audit_log)")
    columns = cursor.fetchall()

    # Convert to dict for easier testing
    column_dict = {col[1]: col[2] for col in columns}

    assert "ts" in column_dict
    assert "user_id" in column_dict
    assert "query_hash" in column_dict
    assert "response_summary" in column_dict

    # Check that ts is the primary key
    pk_columns = [col[1] for col in columns if col[5] == 1]
    assert "ts" in pk_columns


def test_wal_mode_enabled(db_manager):
    """Test that WAL mode is enabled."""
    conn = db_manager.connect()

    cursor = conn.execute("PRAGMA journal_mode")
    result = cursor.fetchone()

    assert result[0].upper() == "WAL"


def test_foreign_keys_enabled(db_manager):
    """Test that foreign keys are enabled."""
    conn = db_manager.connect()

    cursor = conn.execute("PRAGMA foreign_keys")
    result = cursor.fetchone()

    assert result[0] == 1


def test_verify_schema(db_manager):
    """Test schema verification."""
    # Should return True for initialized database
    assert db_manager.verify_schema() is True


def test_verify_schema_empty_db(test_env):
    """Test schema verification on empty database."""
    # Create a database without initializing schema
    db_manager = DatabaseManager()
    db_manager.connect()

    # Should return False since schema not initialized
    assert db_manager.verify_schema() is False

    db_manager.close()


def test_context_manager(test_env):
    """Test that DatabaseManager works as context manager."""
    with DatabaseManager() as db_manager:
        db_manager.initialize_schema()
        assert db_manager.verify_schema() is True

    # Connection should be closed after exiting context
    assert db_manager._connection is None


def test_init_database_function(test_env):
    """Test the init_database convenience function."""
    db_manager = init_database()

    # Should be initialized and valid
    assert db_manager.verify_schema() is True

    db_manager.close()


def test_database_insert_and_query(db_manager):
    """Test basic insert and query operations on audit_log."""
    conn = db_manager.connect()

    # Insert a test record
    ts = 1234567890000
    user_id = "test_user"
    query_hash = "abc123"
    response_summary = "Test response"

    conn.execute(
        "INSERT INTO audit_log (ts, user_id, query_hash, response_summary) VALUES (?, ?, ?, ?)",
        (ts, user_id, query_hash, response_summary)
    )
    conn.commit()

    # Query it back
    cursor = conn.execute("SELECT * FROM audit_log WHERE ts = ?", (ts,))
    row = cursor.fetchone()

    assert row is not None
    assert row[0] == ts
    assert row[1] == user_id
    assert row[2] == query_hash
    assert row[3] == response_summary


def test_multiple_connections(test_env):
    """Test that multiple DatabaseManager instances can coexist."""
    db_manager1 = DatabaseManager()
    db_manager1.initialize_schema()

    db_manager2 = DatabaseManager()
    db_manager2.connect()

    # Both should be able to verify schema
    assert db_manager1.verify_schema() is True
    assert db_manager2.verify_schema() is True

    db_manager1.close()
    db_manager2.close()
