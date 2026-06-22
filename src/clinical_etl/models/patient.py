"""Patient-related Pydantic models."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PatientSource(StrEnum):
    FHIR = "FHIR"
    ORACLE_EHR = "ORACLE_EHR"
    LAB_CSV = "LAB_CSV"
    EDI_837 = "EDI_837"
    MANUAL = "MANUAL"


class PatientMatchCandidate(BaseModel):
    """A patient record coming in from a source system, awaiting MPI matching."""

    model_config = ConfigDict(str_strip_whitespace=True)

    source: PatientSource
    source_id: str = Field(..., min_length=1, max_length=128)

    # Identifiers
    mrn: str | None = Field(None, max_length=64)
    ssn_last4: str | None = Field(None, max_length=4)
    insurance_id: str | None = Field(None, max_length=64)

    # Demographics
    first_name: str = Field(..., min_length=1, max_length=128)
    middle_name: str | None = Field(None, max_length=128)
    last_name: str = Field(..., min_length=1, max_length=128)
    date_of_birth: date
    gender: str | None = Field(None, max_length=16)

    # Contact
    email: str | None = Field(None, max_length=256)
    phone: str | None = Field(None, max_length=32)

    # Address
    address_line1: str | None = Field(None, max_length=256)
    city: str | None = Field(None, max_length=128)
    state: str | None = Field(None, max_length=64)
    postal_code: str | None = Field(None, max_length=20)
    country: str = Field("US", max_length=2)

    # Source tracking
    extracted_at: datetime


class PatientMatchScore(BaseModel):
    """The result of comparing a candidate against an MPI record."""

    candidate_source_id: str
    master_id: str
    composite_score: float = Field(..., ge=0.0, le=1.0)
    name_score: float = Field(..., ge=0.0, le=1.0)
    dob_score: float = Field(..., ge=0.0, le=1.0)
    address_score: float = Field(..., ge=0.0, le=1.0)
    identifier_score: float = Field(..., ge=0.0, le=1.0)
    decision: str  # AUTO_MERGE | REVIEW | NO_MATCH
    explanation: str


class MasterPatient(BaseModel):
    """The canonical patient in the Master Patient Index."""

    model_config = ConfigDict(str_strip_whitespace=True)

    master_id: str = Field(..., min_length=1, max_length=64)

    # Masked demographics (after PHI masking)
    first_name_hash: str | None = None
    last_name_hash: str | None = None
    dob_year: int | None = Field(None, ge=1900, le=2100)
    gender: str | None = None
    zip3: str | None = Field(None, max_length=3)
    state: str | None = None
    country: str = "US"

    # Source linkages (preserved for join-back)
    source_ids: list[str] = Field(default_factory=list)

    # Audit
    first_seen_at: datetime
    last_seen_at: datetime
    merged_from: list[str] = Field(default_factory=list)
