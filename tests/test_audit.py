"""Tests for audit logging functionality."""

import sqlite3
import hashlib
import pytest
from pathlib import Path

from mcp_healthcare.audit import AuditLogger
from mcp_healthcare.db import DatabaseManager
from mcp_healthcare.config import get_settings


@pytest.fixture
def audit_logger(db_manager):
    """Create a test audit logger."""
    return AuditLogger(db_manager)


def test_audit_log_write(audit_logger, db_manager):
    """Test that audit log entries can be written and retrieved."""
    # Write an audit log entry
    user_id = "test_user_123"
    query = "What is the patient's diagnosis?"
    response_summary = "Provided diagnosis information"

    audit_logger.log_query(user_id, query, response_summary)

    # Retrieve the record from database
    conn = db_manager.connect()
    cursor = conn.execute(
        "SELECT user_id, query_hash, response_summary FROM audit_log WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()

    # Verify the record was written
    assert row is not None
    assert row[0] == user_id

    # Verify query is hashed, not stored in plaintext
    expected_hash = hashlib.sha256(query.encode()).hexdigest()
    assert row[1] == expected_hash

    assert row[2] == response_summary


def test_audit_query_hashing(audit_logger):
    """Test that queries are hashed using SHA256."""
    user_id = "test_user_456"
    query = "Sensitive patient query"
    response_summary = "Response provided"

    # Log the query
    audit_logger.log_query(user_id, query, response_summary)

    # Retrieve recent logs
    logs = audit_logger.get_recent_logs(limit=1)

    assert len(logs) == 1
    log_entry = logs[0]

    # Verify the hash matches SHA256
    expected_hash = hashlib.sha256(query.encode()).hexdigest()
    assert log_entry["query_hash"] == expected_hash

    # Verify query is NOT stored in plaintext
    assert query not in str(log_entry)


def test_audit_disabled(db_manager, monkeypatch):
    """Test that audit logging is skipped when MCP_AUDIT_ENABLE=false."""
    # Disable audit logging
    monkeypatch.setenv("MCP_AUDIT_ENABLE", "false")

    # Clear cached settings
    import mcp_healthcare.config
    mcp_healthcare.config._settings = None

    # Create new audit logger with disabled settings
    audit_logger = AuditLogger(db_manager)

    # Attempt to log
    audit_logger.log_query("user_123", "test query", "test response")

    # Verify nothing was written
    conn = db_manager.connect()
    cursor = conn.execute("SELECT COUNT(*) FROM audit_log")
    count = cursor.fetchone()[0]

    assert count == 0

    # Restore settings
    mcp_healthcare.config._settings = None


def test_get_recent_logs(audit_logger, db_manager):
    """Test retrieval of recent audit log entries."""
    # Insert multiple log entries
    for i in range(5):
        audit_logger.log_query(
            f"user_{i}",
            f"query_{i}",
            f"response_{i}"
        )

    # Retrieve recent logs with limit
    logs = audit_logger.get_recent_logs(limit=3)

    assert len(logs) == 3

    # Verify they're in reverse chronological order (most recent first)
    # The most recent should be user_4
    assert logs[0]["user_id"] == "user_4"
    assert logs[1]["user_id"] == "user_3"
    assert logs[2]["user_id"] == "user_2"

    # Verify each log has required fields
    for log in logs:
        assert "ts" in log
        assert "user_id" in log
        assert "query_hash" in log
        assert "response_summary" in log


def test_audit_delete_prevention(db_manager):
    """Test that audit log records cannot be deleted."""
    # Insert a record
    conn = db_manager.connect()
    ts = 1234567890000
    conn.execute(
        "INSERT INTO audit_log (ts, user_id, query_hash, response_summary) VALUES (?, ?, ?, ?)",
        (ts, "test_user", "hash123", "summary")
    )
    conn.commit()

    # Attempt to delete the record - should raise an error
    with pytest.raises(sqlite3.IntegrityError, match="Audit log records cannot be deleted"):
        conn.execute("DELETE FROM audit_log WHERE ts = ?", (ts,))

    # Verify record still exists
    cursor = conn.execute("SELECT COUNT(*) FROM audit_log WHERE ts = ?", (ts,))
    count = cursor.fetchone()[0]
    assert count == 1


def test_audit_update_prevention(db_manager):
    """Test that audit log records cannot be modified."""
    # Insert a record
    conn = db_manager.connect()
    ts = 1234567890001
    original_user = "original_user"
    conn.execute(
        "INSERT INTO audit_log (ts, user_id, query_hash, response_summary) VALUES (?, ?, ?, ?)",
        (ts, original_user, "hash456", "summary")
    )
    conn.commit()

    # Attempt to update the record - should raise an error
    with pytest.raises(sqlite3.IntegrityError, match="Audit log records cannot be modified"):
        conn.execute(
            "UPDATE audit_log SET user_id = ? WHERE ts = ?",
            ("modified_user", ts)
        )

    # Verify record remains unchanged
    cursor = conn.execute("SELECT user_id FROM audit_log WHERE ts = ?", (ts,))
    user_id = cursor.fetchone()[0]
    assert user_id == original_user


def test_audit_log_timestamp(audit_logger, db_manager):
    """Test that timestamps are properly generated."""
    import time

    before_time = int(time.time() * 1000)
    audit_logger.log_query("user_test", "query", "response")
    after_time = int(time.time() * 1000)

    # Retrieve the log
    logs = audit_logger.get_recent_logs(limit=1)
    assert len(logs) == 1

    log_ts = logs[0]["ts"]

    # Verify timestamp is within expected range
    assert before_time <= log_ts <= after_time


def test_audit_log_error_handling():
    """Test that audit logging handles errors gracefully."""
    # Create a database manager with an invalid path (read-only directory)
    invalid_db_path = Path("/dev/null/invalid.db")
    db_manager = DatabaseManager(db_path=invalid_db_path)

    audit_logger = AuditLogger(db_manager)

    # Attempting to log to an invalid path should raise an exception
    with pytest.raises(Exception):
        audit_logger.log_query("user", "query", "response")
