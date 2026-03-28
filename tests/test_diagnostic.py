"""Tests for diagnostic criteria evaluator."""

import pytest
from mcp_healthcare.models import ObservationBundle
from mcp_healthcare.diagnostic import DiagnosticEvaluator


def test_met_criteria(db_manager):
    """Test evaluation when all criteria are met."""
    # Create observations that PASS sepsis_sirs criteria
    observations = ObservationBundle(
        vitals={
            "temperature": 39.0,  # > 38.3 (PASS)
            "heart_rate": 110,    # > 90 (PASS)
            "respiratory_rate": 22,  # > 20 (PASS)
            "bp_systolic": 90
        },
        labs={
            "lactate": 4.0,  # > 2.0 (PASS)
            "wbc": 15000     # > 12000 (PASS)
        },
        history=["diabetes"]
    )

    evaluator = DiagnosticEvaluator(db_manager=db_manager)
    result = evaluator.evaluate(observations, "sepsis_sirs", user_id="test_user")

    # Verify result structure
    assert "passed" in result
    assert "evidence" in result
    assert "ruleset" in result

    # Verify criteria were met
    assert result["passed"] is True
    assert result["ruleset"] == "sepsis_sirs"

    # Verify evidence contains expected information
    assert len(result["evidence"]) > 0
    evidence_str = " ".join(result["evidence"]).lower()
    assert "temperature" in evidence_str
    assert "heart_rate" in evidence_str
    assert "lactate" in evidence_str


def test_missing_labs(db_manager):
    """Test evaluation when required labs are missing."""
    # Create observations MISSING lactate
    observations = ObservationBundle(
        vitals={
            "temperature": 39.0,  # > 38.3 (PASS)
            "heart_rate": 110,    # > 90 (PASS)
            "respiratory_rate": 22  # > 20 (PASS)
        },
        labs={
            "wbc": 15000  # > 12000 (PASS) - but lactate is MISSING
        },
        history=[]
    )

    evaluator = DiagnosticEvaluator(db_manager=db_manager)
    result = evaluator.evaluate(observations, "sepsis_sirs", user_id="test_user")

    # Verify result structure
    assert "passed" in result
    assert "evidence" in result
    assert "ruleset" in result

    # Verify criteria were NOT met due to missing lactate
    assert result["passed"] is False
    assert result["ruleset"] == "sepsis_sirs"

    # Verify evidence mentions missing lactate
    evidence_str = " ".join(result["evidence"]).lower()
    assert "lactate" in evidence_str
    # Should contain "missing" or "fail" for lactate
    assert "missing" in evidence_str or "fail" in evidence_str


def test_audit(db_manager):
    """Test that audit log contains rule set name."""
    # Create simple observations
    observations = ObservationBundle(
        vitals={
            "temperature": 39.0,
            "heart_rate": 110,
            "respiratory_rate": 22
        },
        labs={
            "lactate": 4.0,
            "wbc": 15000
        },
        history=[]
    )

    evaluator = DiagnosticEvaluator(db_manager=db_manager)
    result = evaluator.evaluate(observations, "sepsis_sirs", user_id="test_audit_user")

    # Query audit_log table for most recent entry
    conn = db_manager.connect()
    cursor = conn.execute(
        "SELECT user_id, query_hash, response_summary FROM audit_log ORDER BY ts DESC LIMIT 1"
    )
    row = cursor.fetchone()

    assert row is not None
    user_id, query_hash, response_summary = row

    # Verify audit entry
    assert user_id == "test_audit_user"

    # Verify "sepsis_sirs" appears in response_summary
    # (The query gets hashed, but response_summary should contain the ruleset name)
    assert "sepsis_sirs" in response_summary.lower()
