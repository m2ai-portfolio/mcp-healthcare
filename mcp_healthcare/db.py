"""SQLite database manager for MCP Healthcare."""

import os
import sqlite3
import logging
from pathlib import Path
from typing import Optional

from .config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database connections and initialization."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file. If None, uses settings.
        """
        self.settings = get_settings()
        self.db_path = db_path or self.settings.db_path
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Get or create a database connection.

        Returns:
            SQLite connection object.
        """
        if self._connection is None:
            # Ensure data directory exists
            self.settings.ensure_data_dir()

            # Create connection
            self._connection = sqlite3.connect(str(self.db_path))

            # Set restrictive file permissions (owner read/write only)
            os.chmod(str(self.db_path), 0o600)

            # Enable WAL mode for better concurrency
            self._connection.execute("PRAGMA journal_mode=WAL")

            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys=ON")

            logger.info(f"Connected to database: {self.db_path}")

        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    def initialize_schema(self) -> None:
        """Initialize the database schema."""
        conn = self.connect()

        # Create audit_log table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                ts INTEGER PRIMARY KEY,
                user_id TEXT,
                query_hash TEXT,
                response_summary TEXT
            )
        """)

        # Create triggers to make audit_log truly append-only
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
            BEFORE DELETE ON audit_log
            BEGIN
              SELECT RAISE(ABORT, 'Audit log records cannot be deleted');
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_audit_update
            BEFORE UPDATE ON audit_log
            BEGIN
              SELECT RAISE(ABORT, 'Audit log records cannot be modified');
            END
        """)

        conn.commit()
        logger.info("Database schema initialized")

    def verify_schema(self) -> bool:
        """Verify that the database schema is properly initialized.

        Returns:
            True if schema is valid, False otherwise.
        """
        try:
            conn = self.connect()
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'"
            )
            result = cursor.fetchone()
            return result is not None
        except sqlite3.Error as e:
            logger.error(f"Error verifying schema: {e}")
            return False

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def init_database(db_path: Optional[Path] = None) -> DatabaseManager:
    """Initialize and return a database manager.

    Args:
        db_path: Optional path to database file.

    Returns:
        Initialized DatabaseManager instance.
    """
    db_manager = DatabaseManager(db_path)
    db_manager.initialize_schema()
    return db_manager
