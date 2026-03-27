"""Pydantic data models for MCP Healthcare."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal


class MedicationInput(BaseModel):
    """Input model for medication information."""

    name: str = Field(..., description="Drug name as reported by the prescriber")
    dose: str = Field(..., description="Quantity and unit, e.g., '500 mg'")
    route: str = Field(..., description="Administration route, e.g., 'PO', 'IV'")


class ObservationBundle(BaseModel):
    """Bundle of clinical observations including vitals, labs, and history."""

    vitals: Dict[str, float] = Field(
        ...,
        description="Blood pressure, heart rate, temperature, SpO2"
    )
    labs: Dict[str, float] = Field(
        ...,
        description="Selected laboratory results, e.g., creatinine, lactate"
    )
    history: List[str] = Field(
        ...,
        description="Relevant past diagnoses or procedures"
    )


class InteractionAlert(BaseModel):
    """Alert for drug interactions or contraindications."""

    severity: Literal["contraindication", "warning", "precaution"] = Field(...)
    description: str = Field(
        ...,
        description="Human-readable explanation of the interaction"
    )
    source: str = Field(
        ...,
        description="Reference identifier, e.g., 'Stockley 7e' or 'Micromedex'"
    )


class PathwayStep(BaseModel):
    """Step in a clinical care pathway."""

    action: str = Field(
        ...,
        description="Clinical action, e.g., 'Administer antibiotic', 'Order CBC'"
    )
    detail: str = Field(..., description="Free-text specifics or dosage")
    estimated_hours: Optional[float] = Field(
        None,
        description="Rough time to complete the step"
    )
