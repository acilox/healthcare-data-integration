"""Clinical encounter Pydantic models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DiagnosisCode(BaseModel):
    """ICD-10-CM diagnosis code."""

    code: str = Field(..., min_length=3, max_length=8)
    description: str | None = Field(None, max_length=256)
    category: str | None = Field(None, max_length=64)
    is_valid: bool = False

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.upper().strip().replace(".", "")


class ProcedureCode(BaseModel):
    """CPT procedure code."""

    code: str = Field(..., min_length=5, max_length=5)
    description: str | None = Field(None, max_length=256)
    is_valid: bool = False

    @field_validator("code")
    @classmethod
    def validate_format(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() and not (len(v) == 5 and v[-1].isalpha()):
            # CPT can be 5 digits or 4 digits + 1 letter
            raise ValueError(f"Invalid CPT format: {v!r}")
        return v


class Encounter(BaseModel):
    """A clinical encounter (visit, admission, etc.)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    encounter_id: str = Field(..., min_length=1, max_length=64)
    master_id: str  # Patient MPI link
    encounter_type: str  # AMBULATORY | EMERGENCY | INPATIENT | OUTPATIENT
    encounter_class: str | None = None

    start_datetime: datetime
    end_datetime: datetime | None = None

    provider_id: str | None = Field(None, max_length=64)
    provider_name: str | None = Field(None, max_length=256)
    facility_id: str | None = Field(None, max_length=64)
    facility_name: str | None = Field(None, max_length=256)

    diagnoses: list[DiagnosisCode] = Field(default_factory=list)
    procedures: list[ProcedureCode] = Field(default_factory=list)

    chief_complaint: str | None = Field(None, max_length=512)

    # Cost
    total_charges: Decimal | None = Field(None, ge=0)

    # Source
    source_system: str
    source_extracted_at: datetime
