"""Tests for CodeValidator."""

from __future__ import annotations

from clinical_etl.transform import CodeValidator


def test_valid_icd10():
    v = CodeValidator()
    result = v.validate_icd10("I10")
    assert result.is_valid
    assert result.description == "Hypertension"
    assert result.category == "CIRCULATORY"


def test_valid_icd10_with_period():
    v = CodeValidator()
    result = v.validate_icd10("E11.9")
    assert result.code == "E119"
    assert result.is_valid


def test_invalid_icd10():
    v = CodeValidator()
    result = v.validate_icd10("XYZ123")
    assert not result.is_valid


def test_valid_cpt():
    v = CodeValidator()
    result = v.validate_cpt("99213")
    assert result.is_valid
    assert "Office visit" in result.description


def test_invalid_cpt():
    v = CodeValidator()
    result = v.validate_cpt("ABCDE")
    assert not result.is_valid


def test_validate_batch():
    v = CodeValidator()
    dx, px = v.validate_batch(["I10", "BADCODE"], ["99213", "ZZZZZ"])
    assert dx[0].is_valid
    assert not dx[1].is_valid
    assert px[0].is_valid
    assert not px[1].is_valid
