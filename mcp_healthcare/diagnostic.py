"""Diagnostic criteria evaluator module."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import ObservationBundle
from .db import DatabaseManager
from .audit import AuditLogger

logger = logging.getLogger(__name__)


class DiagnosticEvaluator:
    """Evaluates clinical observations against diagnostic rule sets."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None, audit_logger: Optional[AuditLogger] = None):
        """Initialize the diagnostic evaluator.

        Args:
            db_manager: DatabaseManager instance. If None, creates a new one.
            audit_logger: AuditLogger instance. If None, creates a new one.
        """
        self.db_manager = db_manager or DatabaseManager()
        self.audit_logger = audit_logger or AuditLogger(db_manager=self.db_manager)

    def _load_ruleset(self, ruleset_name: str) -> dict:
        """Load a diagnostic rule set from bundled JSON file.

        Args:
            ruleset_name: Name of the rule set (without .json extension).

        Returns:
            Rule set dictionary.

        Raises:
            FileNotFoundError: If ruleset file doesn't exist.
            ValueError: If ruleset JSON is invalid or missing required structure.
        """
        # Get the path to the bundled ruleset file
        data_dir = Path(__file__).parent / "data" / "rulesets"
        ruleset_file = data_dir / f"{ruleset_name}.json"

        if not ruleset_file.exists():
            raise FileNotFoundError(f"Ruleset not found: {ruleset_file}")

        try:
            with open(ruleset_file, "r") as f:
                ruleset = json.load(f)

            # Validate ruleset structure
            self._validate_ruleset(ruleset, ruleset_name)

            logger.info(f"Loaded ruleset: {ruleset_name}")
            return ruleset
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Failed to load ruleset file: {e}")
            raise ValueError(f"Invalid ruleset JSON: {e}")

    def _validate_ruleset(self, ruleset: dict, ruleset_name: str) -> None:
        """Validate that a ruleset has the required structure.

        Args:
            ruleset: The ruleset dictionary to validate.
            ruleset_name: Name of the ruleset (for error messages).

        Raises:
            ValueError: If the ruleset is missing required keys or has invalid structure.
        """
        # Check for top-level required keys
        if "criteria" not in ruleset:
            raise ValueError(f"Ruleset '{ruleset_name}' missing required 'criteria' section")

        if "evaluation" not in ruleset:
            raise ValueError(f"Ruleset '{ruleset_name}' missing required 'evaluation' section")

        criteria = ruleset["criteria"]

        # Validate each criterion in vitals and labs
        for category in ["vitals", "labs"]:
            if category in criteria:
                for field_name, field_rules in criteria[category].items():
                    # Check that field has conditions if it's required or has rules
                    if "conditions" in field_rules:
                        conditions = field_rules["conditions"]
                        if not isinstance(conditions, list):
                            raise ValueError(f"Ruleset '{ruleset_name}': {category}.{field_name}.conditions must be a list")

                        # Validate each condition has required keys
                        for i, condition in enumerate(conditions):
                            if "operator" not in condition:
                                raise ValueError(f"Ruleset '{ruleset_name}': {category}.{field_name}.conditions[{i}] missing 'operator'")
                            if "value" not in condition:
                                raise ValueError(f"Ruleset '{ruleset_name}': {category}.{field_name}.conditions[{i}] missing 'value'")

    def _evaluate_condition(self, value: float, operator: str, threshold: float) -> bool:
        """Evaluate a single condition.

        Args:
            value: The observed value.
            operator: Comparison operator (">", "<", ">=", "<=", "==").
            threshold: The threshold value.

        Returns:
            True if condition is met, False otherwise.

        Raises:
            ValueError: If operator is not recognized.
        """
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        else:
            raise ValueError(f"Unknown operator: {operator}. Valid operators are: >, <, >=, <=, ==")

    def _evaluate_field(self, field_name: str, field_value: Optional[float], field_rules: dict) -> Tuple[bool, str]:
        """Evaluate a single field against its rules.

        Args:
            field_name: Name of the field being evaluated.
            field_value: The observed value (None if missing).
            field_rules: The rules for this field.

        Returns:
            Tuple of (passed: bool, evidence: str).
        """
        # Check if field is required
        if field_rules.get("required", False) and field_value is None:
            return False, f"Missing required field: {field_name}"

        # If field is not present but not required, skip evaluation
        if field_value is None:
            return True, f"{field_name}: not provided (not required)"

        # Evaluate conditions
        conditions = field_rules.get("conditions", [])
        logic = field_rules.get("logic", "AND")

        if not conditions:
            return True, f"{field_name}: {field_value} (no conditions)"

        results = []
        for condition in conditions:
            operator = condition["operator"]
            threshold = condition["value"]
            result = self._evaluate_condition(field_value, operator, threshold)
            results.append(result)

        # Apply logic (AND or OR)
        if logic == "OR":
            passed = any(results)
        else:  # AND
            passed = all(results)

        # Build evidence string
        conditions_str = " OR ".join([f"{c['operator']}{c['value']}" for c in conditions]) if logic == "OR" else \
                         " AND ".join([f"{c['operator']}{c['value']}" for c in conditions])

        status = "PASS" if passed else "FAIL"
        evidence = f"{field_name}: {field_value} ({conditions_str}) - {status}"

        return passed, evidence

    def evaluate(self, observations: ObservationBundle, ruleset_name: str, user_id: str = "system") -> Dict:
        """Evaluate observations against a diagnostic rule set.

        Args:
            observations: ObservationBundle containing vitals, labs, and history.
            ruleset_name: Name of the diagnostic rule set to use.
            user_id: User ID for audit logging.

        Returns:
            Dictionary with keys:
                - passed (bool): True if all criteria met
                - evidence (List[str]): List of evidence strings
                - ruleset (str): Name of the ruleset used
        """
        try:
            # Load the ruleset
            ruleset = self._load_ruleset(ruleset_name)
        except Exception as e:
            logger.error(f"Failed to load ruleset: {e}")
            result = {
                "passed": False,
                "evidence": [f"ERROR: Failed to load ruleset '{ruleset_name}': {str(e)}"],
                "ruleset": ruleset_name
            }
            self._log_audit(user_id, ruleset_name, observations, result)
            return result

        evidence = []
        sirs_criteria_met = 0
        all_criteria_met = True

        # Evaluate vitals
        vitals_criteria = ruleset.get("criteria", {}).get("vitals", {})
        for field_name, field_rules in vitals_criteria.items():
            field_value = observations.vitals.get(field_name)
            passed, field_evidence = self._evaluate_field(field_name, field_value, field_rules)
            evidence.append(field_evidence)

            # Count SIRS criteria (temperature, heart_rate, respiratory_rate from vitals)
            if field_name in ["temperature", "heart_rate", "respiratory_rate"]:
                if passed and field_value is not None:
                    sirs_criteria_met += 1

            if not passed:
                all_criteria_met = False

        # Evaluate labs
        labs_criteria = ruleset.get("criteria", {}).get("labs", {})
        for field_name, field_rules in labs_criteria.items():
            field_value = observations.labs.get(field_name)
            passed, field_evidence = self._evaluate_field(field_name, field_value, field_rules)
            evidence.append(field_evidence)

            # Count WBC as a SIRS criterion
            if field_name == "wbc":
                if passed and field_value is not None:
                    sirs_criteria_met += 1

            if not passed:
                all_criteria_met = False

        # Check minimum SIRS criteria requirement
        evaluation_config = ruleset.get("evaluation", {})
        minimum_sirs = evaluation_config.get("minimum_sirs_criteria", 0)

        if minimum_sirs > 0:
            sirs_check_passed = sirs_criteria_met >= minimum_sirs
            evidence.append(f"SIRS criteria met: {sirs_criteria_met}/{minimum_sirs} required - {'PASS' if sirs_check_passed else 'FAIL'}")
            if not sirs_check_passed:
                all_criteria_met = False

        # Build result
        result = {
            "passed": all_criteria_met,
            "evidence": evidence,
            "ruleset": ruleset_name
        }

        # Log audit record
        self._log_audit(user_id, ruleset_name, observations, result)

        return result

    def _log_audit(self, user_id: str, ruleset_name: str, observations: ObservationBundle, result: Dict) -> None:
        """Log audit record for the diagnostic evaluation.

        Args:
            user_id: User ID making the request.
            ruleset_name: Name of the ruleset evaluated.
            observations: The observation bundle that was evaluated.
            result: The evaluation result.
        """
        # Create query string with field names only (no PHI values)
        vitals_fields = list(observations.vitals.keys())
        labs_fields = list(observations.labs.keys())
        query = f"diagnostic_evaluation: ruleset={ruleset_name}, fields=[{', '.join(vitals_fields + labs_fields)}]"

        # Create response summary with ruleset name
        response_summary = f"ruleset={ruleset_name}, passed={result['passed']}, evidence_count={len(result['evidence'])}"

        # Log the audit record
        try:
            self.audit_logger.log_query(user_id, query, response_summary)
        except Exception as e:
            logger.error(f"Failed to log audit record: {e}")
            # Don't raise - audit failure shouldn't block the evaluation
