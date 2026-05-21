"""Tests for PHI masker."""

from __future__ import annotations

from datetime import date

from clinical_etl.transform import PHIMasker


def test_hash_name_deterministic():
    m = PHIMasker()
    h1 = m.hash_name("Alice")
    h2 = m.hash_name("alice")
    h3 = m.hash_name(" Alice ")
    assert h1 == h2 == h3  # case+whitespace normalized


def test_hash_name_different_inputs_different_outputs():
    m = PHIMasker()
    assert m.hash_name("Alice") != m.hash_name("Bob")


def test_mask_dob_year_only():
    m = PHIMasker()
    assert m.mask_dob(date(1985, 6, 15)) == 1985


def test_mask_dob_over_89_is_none():
    m = PHIMasker()
    # 1900 birthdate is definitely over 89
    assert m.mask_dob(date(1900, 1, 1)) is None


def test_mask_zip_truncates_to_3():
    m = PHIMasker()
    assert m.mask_zip("02101") == "021"
    assert m.mask_zip("02") is None
    assert m.mask_zip("") is None


def test_mask_ssn_keeps_last4():
    m = PHIMasker()
    assert m.mask_ssn("123-45-6789") == "6789"
    assert m.mask_ssn("XX") is None


def test_mask_email_keeps_domain():
    m = PHIMasker()
    assert m.mask_email("alice@example.com") == "***@example.com"


def test_mask_text_redacts_pii():
    m = PHIMasker()
    text = "Contact alice@example.com or 555-123-4567 about SSN 123-45-6789"
    out = m.mask_text(text)
    assert "alice@example.com" not in out
    assert "123-45-6789" not in out
    assert "555-123-4567" not in out
    assert "REDACTED" in out


def test_mask_patient_record_full(candidate_alice):
    m = PHIMasker()
    out = m.mask_patient_record(candidate_alice.model_dump())
    # PHI fields are gone
    assert "first_name" not in out
    assert "last_name" not in out
    assert "address_line1" not in out
    assert "city" not in out
    # Replaced with masked versions
    assert "first_name_hash" in out
    assert out["dob_year"] == 1985
    assert out["zip3"] == "021"
    assert "@example.com" in out["email"]
