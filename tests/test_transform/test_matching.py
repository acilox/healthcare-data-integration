"""Tests for PatientMatcher."""

from __future__ import annotations

from datetime import UTC, date

from clinical_etl.transform import PatientMatcher


def test_jaro_winkler_basic():
    assert PatientMatcher.compare_names_jw("Alice", "Alice") == 1.0
    similarity = PatientMatcher.compare_names_jw("Alice", "Alyce")
    assert 0.5 < similarity < 1.0


def test_dob_within_tolerance():
    assert PatientMatcher.dob_within_tolerance(date(2020, 1, 1), date(2020, 1, 1))
    assert PatientMatcher.dob_within_tolerance(date(2020, 1, 1), date(2020, 1, 2))
    assert not PatientMatcher.dob_within_tolerance(date(2020, 1, 1), date(2020, 1, 3))


def test_exact_match_auto_merge(candidate_alice, master_alice):
    matcher = PatientMatcher()
    score = matcher.score(candidate_alice, master_alice)
    # Same source_id linkage => identifier_score=1.0; same DOB year, same ZIP3, same state
    assert score.decision == "AUTO_MERGE"
    assert score.composite_score >= 0.85


def test_mismatched_candidate(master_alice):
    from datetime import datetime

    from clinical_etl.models import PatientMatchCandidate, PatientSource

    candidate = PatientMatchCandidate(
        source=PatientSource.LAB_CSV,
        source_id="UNRELATED-ID",
        first_name="Zorro",
        last_name="Zebra",
        date_of_birth=date(1950, 1, 1),
        state="CA",
        postal_code="90001",
        extracted_at=datetime.now(tz=UTC),
    )
    matcher = PatientMatcher()
    score = matcher.score(candidate, master_alice)
    assert score.decision == "NO_MATCH"
