"""HIPAA audit logging functionality."""

import time
import hashlib
import logging
from typing import Optional

from .config import get_settings
from .db import DatabaseManager

logger = logging.getLogger(__name__)


class AuditLogger:
    """HIPAA-compliant audit logger."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the audit logger.

        Args:
            db_manager: DatabaseManager instance. If None, creates a new one.
        """
        self.settings = get_settings()
        self.db_manager = db_manager or DatabaseManager()

    def log_query(
        self,
        user_id: str,
        query: str,
        response_summary: str
    ) -> None:
        """Log a clinical query for HIPAA compliance.

        Args:
            user_id: Identifier for the user making the query.
            query: The clinical query or request.
            response_summary: Summary of the response provided.
        """
        if not self.settings.mcp_audit_enable:
            logger.debug("Audit logging is disabled")
            return

        # Generate timestamp (milliseconds since epoch)
        ts = int(time.time() * 1000)

        # Hash the query for privacy
        query_hash = hashlib.sha256(query.encode()).hexdigest()

        # Insert into audit log
        try:
            conn = self.db_manager.connect()
            conn.execute(
                """
                INSERT INTO audit_log (ts, user_id, query_hash, response_summary)
                VALUES (?, ?, ?, ?)
                """,
                (ts, user_id, query_hash, response_summary)
            )
            conn.commit()
            logger.info("Audit log entry created successfully")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            raise

    def get_recent_logs(self, limit: int = 10):
        """Retrieve recent audit log entries.

        Args:
            limit: Maximum number of entries to retrieve.

        Returns:
            List of audit log entries as dictionaries.
        """
        try:
            conn = self.db_manager.connect()
            cursor = conn.execute(
                """
                SELECT ts, user_id, query_hash, response_summary
                FROM audit_log
                ORDER BY ts DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            return [
                {
                    "ts": row[0],
                    "user_id": row[1],
                    "query_hash": row[2],
                    "response_summary": row[3]
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {e}")
            return []
