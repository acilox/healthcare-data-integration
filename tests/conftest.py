"""Shared fixtures for Clinical ETL tests."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from clinical_etl.models import MasterPatient, PatientMatchCandidate, PatientSource


@pytest.fixture
def candidate_alice() -> PatientMatchCandidate:
    return PatientMatchCandidate(
        source=PatientSource.FHIR,
        source_id="FHIR-P-001",
        mrn="MRN-100",
        first_name="Alice",
        last_name="Anderson",
        date_of_birth=date(1985, 6, 15),
        gender="female",
        email="alice@example.com",
        phone="555-123-4567",
        address_line1="123 Main St",
        city="Boston",
        state="MA",
        postal_code="02101",
        country="US",
        extracted_at=datetime.now(tz=timezone.utc),
    )


@pytest.fixture
def master_alice() -> MasterPatient:
    return MasterPatient(
        master_id="MPI-001",
        first_name_hash="alicehash00",
        last_name_hash="andersonhash",
        dob_year=1985,
        gender="female",
        zip3="021",
        state="MA",
        country="US",
        source_ids=["FHIR-P-001", "ORACLE-XYZ"],
        first_seen_at=datetime.now(tz=timezone.utc),
        last_seen_at=datetime.now(tz=timezone.utc),
    )
