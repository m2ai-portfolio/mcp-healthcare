"""Tests for drug interaction checker functionality."""

import pytest
from mcp_healthcare.models import MedicationInput
from mcp_healthcare.drug_checker import DrugInteractionChecker


def test_empty_list(db_manager):
    """Empty medication list returns no interactions."""
    checker = DrugInteractionChecker(db_manager=db_manager)
    result = checker.check_interactions([])
    assert result == []


def test_known_interaction(db_manager):
    """Known drug pair returns correct interaction alert."""
    checker = DrugInteractionChecker(db_manager=db_manager)

    medications = [
        MedicationInput(name="warfarin", dose="5mg", route="PO"),
        MedicationInput(name="aspirin", dose="81mg", route="PO")
    ]

    alerts = checker.check_interactions(medications, user_id="test-user")

    # Should return exactly one alert
    assert len(alerts) == 1

    # Check that it's a contraindication
    alert = alerts[0]
    assert alert.severity == "contraindication"
    assert "warfarin" in alert.description.lower() or "aspirin" in alert.description.lower()
    assert alert.source is not None


def test_audit_write(db_manager):
    """Drug check writes audit log entry."""
    checker = DrugInteractionChecker(db_manager=db_manager)

    # Count audit log entries before
    conn = db_manager.connect()
    cursor = conn.execute("SELECT COUNT(*) FROM audit_log")
    count_before = cursor.fetchone()[0]

    # Run a check
    medications = [
        MedicationInput(name="warfarin", dose="5mg", route="PO"),
        MedicationInput(name="aspirin", dose="81mg", route="PO")
    ]
    checker.check_interactions(medications, user_id="audit-test-user")

    # Count audit log entries after
    cursor = conn.execute("SELECT COUNT(*) FROM audit_log")
    count_after = cursor.fetchone()[0]

    # Should have one new entry
    assert count_after == count_before + 1

    # Verify the entry has correct user_id and result_count
    cursor = conn.execute(
        "SELECT user_id, response_summary FROM audit_log ORDER BY ts DESC LIMIT 1"
    )
    row = cursor.fetchone()
    assert row[0] == "audit-test-user"
    assert "result_count=1" in row[1]


def test_single_medication(db_manager):
    """Single medication returns no interactions."""
    checker = DrugInteractionChecker(db_manager=db_manager)

    medications = [
        MedicationInput(name="warfarin", dose="5mg", route="PO")
    ]

    alerts = checker.check_interactions(medications, user_id="test-user")
    assert alerts == []


def test_multiple_interactions(db_manager):
    """Multiple drugs with multiple interactions."""
    checker = DrugInteractionChecker(db_manager=db_manager)

    medications = [
        MedicationInput(name="warfarin", dose="5mg", route="PO"),
        MedicationInput(name="aspirin", dose="81mg", route="PO"),
        MedicationInput(name="simvastatin", dose="20mg", route="PO"),
        MedicationInput(name="erythromycin", dose="500mg", route="PO")
    ]

    alerts = checker.check_interactions(medications, user_id="test-user")

    # Should have at least 2 interactions:
    # 1. warfarin + aspirin
    # 2. simvastatin + erythromycin
    assert len(alerts) >= 2

    # Check that we have contraindications
    severities = [alert.severity for alert in alerts]
    assert "contraindication" in severities


def test_no_interaction(db_manager):
    """Drugs that don't interact return no alerts."""
    checker = DrugInteractionChecker(db_manager=db_manager)

    medications = [
        MedicationInput(name="metformin", dose="500mg", route="PO"),
        MedicationInput(name="lisinopril", dose="10mg", route="PO")
    ]

    alerts = checker.check_interactions(medications, user_id="test-user")
    assert len(alerts) == 0


def test_case_insensitive(db_manager):
    """Drug names should match regardless of case."""
    checker = DrugInteractionChecker(db_manager=db_manager)

    # Test with uppercase drug names
    medications = [
        MedicationInput(name="WARFARIN", dose="5mg", route="PO"),
        MedicationInput(name="ASPIRIN", dose="81mg", route="PO")
    ]

    alerts = checker.check_interactions(medications, user_id="test-user")
    assert len(alerts) == 1
    assert alerts[0].severity == "contraindication"

    # Test with mixed case
    medications = [
        MedicationInput(name="Warfarin", dose="5mg", route="PO"),
        MedicationInput(name="Aspirin", dose="81mg", route="PO")
    ]

    alerts = checker.check_interactions(medications, user_id="test-user")
    assert len(alerts) == 1
    assert alerts[0].severity == "contraindication"


def test_interaction_bidirectional(db_manager):
    """Interaction should be found regardless of drug order."""
    checker = DrugInteractionChecker(db_manager=db_manager)

    # Test order A, B
    medications_ab = [
        MedicationInput(name="warfarin", dose="5mg", route="PO"),
        MedicationInput(name="aspirin", dose="81mg", route="PO")
    ]

    alerts_ab = checker.check_interactions(medications_ab, user_id="test-user")

    # Test order B, A
    medications_ba = [
        MedicationInput(name="aspirin", dose="81mg", route="PO"),
        MedicationInput(name="warfarin", dose="5mg", route="PO")
    ]

    alerts_ba = checker.check_interactions(medications_ba, user_id="test-user")

    # Should find the same interaction regardless of order
    assert len(alerts_ab) == len(alerts_ba) == 1
    assert alerts_ab[0].severity == alerts_ba[0].severity == "contraindication"


def test_warning_severity(db_manager):
    """Test warning severity interactions."""
    checker = DrugInteractionChecker(db_manager=db_manager)

    medications = [
        MedicationInput(name="metformin", dose="500mg", route="PO"),
        MedicationInput(name="contrast dye", dose="100ml", route="IV")
    ]

    alerts = checker.check_interactions(medications, user_id="test-user")
    assert len(alerts) == 1
    assert alerts[0].severity == "warning"


def test_precaution_severity(db_manager):
    """Test precaution severity interactions."""
    checker = DrugInteractionChecker(db_manager=db_manager)

    medications = [
        MedicationInput(name="ciprofloxacin", dose="500mg", route="PO"),
        MedicationInput(name="theophylline", dose="300mg", route="PO")
    ]

    alerts = checker.check_interactions(medications, user_id="test-user")
    assert len(alerts) == 1
    assert alerts[0].severity == "precaution"
