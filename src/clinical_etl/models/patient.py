"""Patient-related Pydantic models."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PatientSource(str, Enum):
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
    mrn: Optional[str] = Field(None, max_length=64)
    ssn_last4: Optional[str] = Field(None, max_length=4)
    insurance_id: Optional[str] = Field(None, max_length=64)

    # Demographics
    first_name: str = Field(..., min_length=1, max_length=128)
    middle_name: Optional[str] = Field(None, max_length=128)
    last_name: str = Field(..., min_length=1, max_length=128)
    date_of_birth: date
    gender: Optional[str] = Field(None, max_length=16)

    # Contact
    email: Optional[str] = Field(None, max_length=256)
    phone: Optional[str] = Field(None, max_length=32)

    # Address
    address_line1: Optional[str] = Field(None, max_length=256)
    city: Optional[str] = Field(None, max_length=128)
    state: Optional[str] = Field(None, max_length=64)
    postal_code: Optional[str] = Field(None, max_length=20)
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
    first_name_hash: Optional[str] = None
    last_name_hash: Optional[str] = None
    dob_year: Optional[int] = Field(None, ge=1900, le=2100)
    gender: Optional[str] = None
    zip3: Optional[str] = Field(None, max_length=3)
    state: Optional[str] = None
    country: str = "US"

    # Source linkages (preserved for join-back)
    source_ids: list[str] = Field(default_factory=list)

    # Audit
    first_seen_at: datetime
    last_seen_at: datetime
    merged_from: list[str] = Field(default_factory=list)
