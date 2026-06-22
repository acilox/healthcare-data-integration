"""Claim & remittance Pydantic models for EDI 837/835."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ClaimLine(BaseModel):
    """A line item on a claim (837)."""

    line_number: int = Field(..., ge=1)
    procedure_code: str = Field(..., max_length=8)
    modifiers: list[str] = Field(default_factory=list)
    diagnosis_pointers: list[int] = Field(default_factory=list)
    units: int = Field(..., ge=1)
    charge_amount: Decimal = Field(..., ge=0)
    service_date: date


class Claim(BaseModel):
    """EDI 837 claim."""

    model_config = ConfigDict(str_strip_whitespace=True)

    claim_id: str = Field(..., min_length=1, max_length=64)
    master_id: str
    submitter_id: str | None = Field(None, max_length=64)
    payer_id: str = Field(..., max_length=64)

    statement_from: date
    statement_to: date

    diagnoses: list[str] = Field(default_factory=list)
    lines: list[ClaimLine] = Field(default_factory=list)

    total_charges: Decimal = Field(..., ge=0)
    claim_type: str  # PROFESSIONAL | INSTITUTIONAL | DENTAL
    submitted_at: datetime
    source_system: str = "EDI_837"


class RemittanceAdvice(BaseModel):
    """EDI 835 remittance reconciled against a claim."""

    model_config = ConfigDict(str_strip_whitespace=True)

    remittance_id: str
    claim_id: str
    payer_id: str
    payment_method: str  # ACH | CHECK | CREDIT_CARD
    payment_amount: Decimal = Field(..., ge=0)
    payment_date: date

    provider_paid: Decimal = Field(..., ge=0)
    patient_responsibility: Decimal = Field(..., ge=0)
    contractual_adjustment: Decimal = Field(..., ge=0)
    denied_amount: Decimal = Field(default=Decimal("0"), ge=0)
    denial_reasons: list[str] = Field(default_factory=list)

    received_at: datetime
    source_system: str = "EDI_835"
