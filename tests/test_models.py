"""Tests for Pydantic data models."""

import pytest
from pydantic import ValidationError

from mcp_healthcare.models import (
    MedicationInput,
    ObservationBundle,
    InteractionAlert,
    PathwayStep,
)


def test_medication_input_valid():
    """Test that MedicationInput accepts valid data."""
    med = MedicationInput(
        name="Amoxicillin",
        dose="500 mg",
        route="PO"
    )

    assert med.name == "Amoxicillin"
    assert med.dose == "500 mg"
    assert med.route == "PO"


def test_medication_input_missing_field():
    """Test that MedicationInput requires all fields."""
    with pytest.raises(ValidationError):
        MedicationInput(name="Amoxicillin", dose="500 mg")


def test_observation_bundle_valid():
    """Test that ObservationBundle accepts valid data."""
    obs = ObservationBundle(
        vitals={"bp_systolic": 120, "bp_diastolic": 80, "hr": 72},
        labs={"creatinine": 1.0, "lactate": 1.5},
        history=["Type 2 Diabetes", "Hypertension"]
    )

    assert obs.vitals["bp_systolic"] == 120
    assert obs.labs["creatinine"] == 1.0
    assert "Type 2 Diabetes" in obs.history


def test_interaction_alert_valid():
    """Test that InteractionAlert accepts valid data."""
    alert = InteractionAlert(
        severity="warning",
        description="May increase risk of QT prolongation",
        source="Micromedex"
    )

    assert alert.severity == "warning"
    assert alert.description == "May increase risk of QT prolongation"
    assert alert.source == "Micromedex"


def test_interaction_alert_severity_validation():
    """Test that InteractionAlert validates severity field."""
    # Valid severities
    for severity in ["contraindication", "warning", "precaution"]:
        alert = InteractionAlert(
            severity=severity,
            description="Test",
            source="Test"
        )
        assert alert.severity == severity

    # Invalid severity should raise error
    with pytest.raises(ValidationError):
        InteractionAlert(
            severity="invalid_severity",
            description="Test",
            source="Test"
        )


def test_pathway_step_valid():
    """Test that PathwayStep accepts valid data."""
    step = PathwayStep(
        action="Administer antibiotic",
        detail="Ceftriaxone 1g IV",
        estimated_hours=0.5
    )

    assert step.action == "Administer antibiotic"
    assert step.detail == "Ceftriaxone 1g IV"
    assert step.estimated_hours == 0.5


def test_pathway_step_optional_hours():
    """Test that PathwayStep allows optional estimated_hours."""
    step = PathwayStep(
        action="Order CBC",
        detail="Complete blood count with differential"
    )

    assert step.action == "Order CBC"
    assert step.estimated_hours is None


def test_model_json_serialization():
    """Test that models can be serialized to JSON."""
    med = MedicationInput(
        name="Aspirin",
        dose="81 mg",
        route="PO"
    )

    json_str = med.model_dump_json()
    assert "Aspirin" in json_str
    assert "81 mg" in json_str


def test_model_dict_conversion():
    """Test that models can be converted to dictionaries."""
    alert = InteractionAlert(
        severity="contraindication",
        description="Do not combine",
        source="Stockley 7e"
    )

    alert_dict = alert.model_dump()
    assert isinstance(alert_dict, dict)
    assert alert_dict["severity"] == "contraindication"
