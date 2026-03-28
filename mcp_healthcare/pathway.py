"""Care pathway recommender module."""

import json
import logging
from pathlib import Path
from typing import List, Optional

from .models import PathwayStep
from .db import DatabaseManager
from .audit import AuditLogger

logger = logging.getLogger(__name__)


class CarePathwayRecommender:
    """Recommends care pathways using bundled guideline data."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None, audit_logger: Optional[AuditLogger] = None):
        """Initialize the care pathway recommender.

        Args:
            db_manager: DatabaseManager instance. If None, creates a new one.
            audit_logger: AuditLogger instance. If None, creates a new one.
        """
        self.db_manager = db_manager or DatabaseManager()
        self.audit_logger = audit_logger or AuditLogger(db_manager=self.db_manager)
        self.pathways = self._load_all_pathways()  # Cache at init

    def recommend(self, diagnosis: str, context: dict, user_id: str = "system") -> List[PathwayStep]:
        """Recommend care pathway steps for a given diagnosis.

        Args:
            diagnosis: The diagnosis name (e.g., 'pneumonia').
            context: Patient context dictionary (for future use; not used in v1).
            user_id: User ID for audit logging.

        Returns:
            List of PathwayStep objects for the recommended pathway.
            Empty list if diagnosis is not supported.

        Raises:
            ValueError: If diagnosis is invalid (empty, too long, or contains path characters).
        """
        # Input validation
        diagnosis_stripped = diagnosis.strip()

        if not diagnosis_stripped:
            raise ValueError("Diagnosis cannot be empty")

        if len(diagnosis_stripped) > 100:
            raise ValueError("Diagnosis is too long (maximum 100 characters)")

        if "/" in diagnosis_stripped or "\\" in diagnosis_stripped:
            raise ValueError("Diagnosis contains invalid characters (path separators not allowed)")

        # Normalize diagnosis (lowercase, strip whitespace)
        diagnosis_normalized = diagnosis_stripped.lower()

        # Look up pathway data from cache
        pathway_data = self.pathways.get(diagnosis_normalized)

        if pathway_data:
            # Extract steps from pathway data (already validated during load)
            steps = []
            for step_data in pathway_data.get("steps", []):
                step = PathwayStep(
                    action=step_data["action"],
                    detail=step_data["detail"],
                    estimated_hours=step_data.get("estimated_hours")
                )
                steps.append(step)

            # Log audit record
            self._log_audit(user_id, diagnosis_normalized, steps)
            logger.info(f"Pathway recommendation: {diagnosis_normalized} ({len(steps)} steps)")
            return steps
        else:
            # Diagnosis not supported - log warning and return empty list
            logger.warning(f"Unsupported diagnosis: {diagnosis_normalized}")
            self._log_audit(user_id, diagnosis_normalized, [])
            return []

    def _load_all_pathways(self) -> dict:
        """Load all pathway JSON files from the data directory.

        Returns:
            Dictionary mapping diagnosis names (lowercase) to pathway data.
        """
        data_dir = Path(__file__).parent / "data" / "pathways"
        pathways = {}

        if not data_dir.exists():
            logger.warning(f"Pathways directory not found: {data_dir}")
            return pathways

        for filepath in data_dir.glob("*.json"):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)

                # Validate pathway structure before caching
                self._validate_pathway(data)

                # Use filename stem (without .json) as the diagnosis key
                diagnosis = filepath.stem.lower()
                pathways[diagnosis] = data
                logger.info(f"Loaded pathway: {diagnosis}")

            except ValueError as e:
                # Validation error - don't include this pathway
                logger.error(f"Invalid pathway structure in {filepath}: {e}")
            except Exception as e:
                # Loading error - don't include this pathway
                logger.error(f"Failed to load pathway {filepath}: {e}")

        return pathways

    def _validate_pathway(self, data: dict) -> None:
        """Validate pathway data structure.

        Args:
            data: Pathway dictionary to validate.

        Raises:
            ValueError: If pathway structure is invalid.
        """
        if "steps" not in data:
            raise ValueError("Pathway must contain 'steps' key")

        if not isinstance(data["steps"], list):
            raise ValueError("'steps' must be a list")

        if len(data["steps"]) == 0:
            raise ValueError("Pathway must contain at least one step")

        for i, step in enumerate(data["steps"]):
            if not isinstance(step, dict):
                raise ValueError(f"Step {i} must be a dictionary")

            if "action" not in step:
                raise ValueError(f"Step {i} missing required field 'action'")

            if "detail" not in step:
                raise ValueError(f"Step {i} missing required field 'detail'")

            if not isinstance(step["action"], str):
                raise ValueError(f"Step {i} 'action' must be a string")

            if not isinstance(step["detail"], str):
                raise ValueError(f"Step {i} 'detail' must be a string")

            if "estimated_hours" in step and step["estimated_hours"] is not None:
                if not isinstance(step["estimated_hours"], (int, float)):
                    raise ValueError(f"Step {i} 'estimated_hours' must be numeric")

    def _log_audit(self, user_id: str, diagnosis: str, steps: List[PathwayStep]) -> None:
        """Log audit record for the pathway recommendation.

        Args:
            user_id: User ID making the request.
            diagnosis: The diagnosis that was queried.
            steps: List of pathway steps that were recommended.
        """
        # Create query string (NO actual context values - PHI protection)
        query = f"pathway_recommendation: diagnosis={diagnosis}"

        # Create response summary
        response_summary = f"recommendation_count={len(steps)}"

        # Log the audit record
        try:
            self.audit_logger.log_query(user_id, query, response_summary)
        except Exception as e:
            logger.error(f"Failed to log audit record: {e}")
            # Don't raise - audit failure shouldn't block the recommendation
