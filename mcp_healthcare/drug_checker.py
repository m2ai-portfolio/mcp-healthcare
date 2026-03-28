"""Drug interaction checker module."""

import json
import logging
from pathlib import Path
from typing import List, Optional

from .models import MedicationInput, InteractionAlert
from .db import DatabaseManager
from .audit import AuditLogger

logger = logging.getLogger(__name__)


class DrugInteractionChecker:
    """Checks for drug interactions using bundled reference data."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None, audit_logger: Optional[AuditLogger] = None):
        """Initialize the drug interaction checker.

        Args:
            db_manager: DatabaseManager instance. If None, creates a new one.
            audit_logger: AuditLogger instance. If None, creates a new one.
        """
        self.db_manager = db_manager or DatabaseManager()
        self.audit_logger = audit_logger or AuditLogger(db_manager=self.db_manager)
        self.interactions = self._load_interactions()

    def _load_interactions(self) -> List[dict]:
        """Load drug interaction data from bundled JSON file.

        Returns:
            List of interaction dictionaries.
        """
        # Get the path to the bundled interactions.json file
        data_dir = Path(__file__).parent / "data"
        interactions_file = data_dir / "interactions.json"

        if not interactions_file.exists():
            logger.warning(f"Interactions file not found: {interactions_file}")
            return []

        try:
            with open(interactions_file, "r") as f:
                interactions = json.load(f)
            logger.info(f"Loaded {len(interactions)} interaction records")
            return interactions
        except Exception as e:
            logger.error(f"Failed to load interactions file: {e}")
            return []

    def check_interactions(self, medications: List[MedicationInput], user_id: str = "system") -> List[InteractionAlert]:
        """Check for drug interactions among a list of medications.

        Args:
            medications: List of MedicationInput objects to check.
            user_id: User ID for audit logging.

        Returns:
            List of InteractionAlert objects for any detected interactions.
        """
        alerts = []

        # Empty list or single medication - no interactions possible
        if len(medications) < 2:
            self._log_audit(user_id, medications, alerts)
            return alerts

        # Check all pairs of medications
        for i in range(len(medications)):
            for j in range(i + 1, len(medications)):
                med_a = medications[i]
                med_b = medications[j]

                # Check for interaction between this pair
                interaction = self._find_interaction(med_a.name, med_b.name)
                if interaction:
                    alert = InteractionAlert(
                        severity=interaction["severity"],
                        description=interaction["description"],
                        source=interaction["source"]
                    )
                    alerts.append(alert)
                    logger.info(f"Interaction found: {med_a.name} <-> {med_b.name} ({interaction['severity']})")

        # Log audit record
        self._log_audit(user_id, medications, alerts)

        return alerts

    def _find_interaction(self, drug_a: str, drug_b: str) -> Optional[dict]:
        """Find an interaction between two drugs.

        Args:
            drug_a: Name of first drug.
            drug_b: Name of second drug.

        Returns:
            Interaction dictionary if found, None otherwise.
        """
        # Normalize drug names (case-insensitive comparison)
        drug_a_lower = drug_a.lower().strip()
        drug_b_lower = drug_b.lower().strip()

        for interaction in self.interactions:
            int_drug_a = interaction["drug_a"].lower().strip()
            int_drug_b = interaction["drug_b"].lower().strip()

            # Check both orderings (drug_a with drug_b and drug_b with drug_a)
            if (drug_a_lower == int_drug_a and drug_b_lower == int_drug_b) or \
               (drug_a_lower == int_drug_b and drug_b_lower == int_drug_a):
                return interaction

        return None

    def _log_audit(self, user_id: str, medications: List[MedicationInput], alerts: List[InteractionAlert]) -> None:
        """Log audit record for the drug interaction check.

        Args:
            user_id: User ID making the request.
            medications: List of medications that were checked.
            alerts: List of interaction alerts found.
        """
        # Create query string from medication names
        med_names = [med.name for med in medications]
        query = f"drug_interaction_check: {', '.join(med_names)}"

        # Create response summary
        response_summary = f"result_count={len(alerts)}"

        # Log the audit record
        try:
            self.audit_logger.log_query(user_id, query, response_summary)
        except Exception as e:
            logger.error(f"Failed to log audit record: {e}")
            # Don't raise - audit failure shouldn't block the check
