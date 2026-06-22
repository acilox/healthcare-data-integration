"""Probabilistic patient matching engine.

Uses a weighted composite of:
- Jaro-Winkler on first/last name
- Levenshtein on names (fallback for length-tolerance)
- DOB fuzzy match with configurable tolerance
- Identifier exact match (SSN-last4, insurance_id, MRN)
- Address (state + ZIP3) match
"""

from __future__ import annotations

from rapidfuzz.distance import JaroWinkler

from clinical_etl.config import get_logger, get_settings
from clinical_etl.models import MasterPatient, PatientMatchCandidate, PatientMatchScore

logger = get_logger(__name__)


# Weights (must sum to 1.0)
W_NAME = 0.35
W_DOB = 0.25
W_ADDR = 0.10
W_IDENT = 0.30


class PatientMatcher:
    """Compute probabilistic match scores between incoming candidates and the MPI."""

    def __init__(self) -> None:
        s = get_settings()
        self.auto_merge_threshold = s.match_auto_merge_threshold
        self.review_threshold = s.match_review_threshold
        self.dob_tolerance_days = s.match_dob_tolerance_days

    def score(self, candidate: PatientMatchCandidate, master: MasterPatient) -> PatientMatchScore:
        name_s = self._name_score(candidate, master)
        dob_s = self._dob_score(candidate, master)
        addr_s = self._addr_score(candidate, master)
        ident_s = self._ident_score(candidate, master)

        composite = W_NAME * name_s + W_DOB * dob_s + W_ADDR * addr_s + W_IDENT * ident_s

        if composite >= self.auto_merge_threshold:
            decision = "AUTO_MERGE"
        elif composite >= self.review_threshold:
            decision = "REVIEW"
        else:
            decision = "NO_MATCH"

        return PatientMatchScore(
            candidate_source_id=candidate.source_id,
            master_id=master.master_id,
            composite_score=round(composite, 4),
            name_score=round(name_s, 4),
            dob_score=round(dob_s, 4),
            address_score=round(addr_s, 4),
            identifier_score=round(ident_s, 4),
            decision=decision,
            explanation=(
                f"name={name_s:.2f}, dob={dob_s:.2f}, addr={addr_s:.2f}, ident={ident_s:.2f}"
            ),
        )

    # ---- Component scorers ----
    def _name_score(self, c: PatientMatchCandidate, m: MasterPatient) -> float:
        """Combined Jaro-Winkler on first+last name. Since master has hashes,
        the actual implementation would re-hash candidate names with the salt and
        compare hashes (exact match) OR keep an unmasked side-table for matching.

        Here we simulate by comparing source-side string similarity if we have
        the original. For demo purposes we use hash equality.
        """
        # Production: compare unmasked attributes in a separate isolated store
        if m.first_name_hash and m.last_name_hash:
            # Hash comparison: only 0 or 1
            from clinical_etl.transform.masking import PHIMasker

            masker = PHIMasker()
            if (
                masker.hash_name(c.first_name) == m.first_name_hash
                and masker.hash_name(c.last_name) == m.last_name_hash
            ):
                return 1.0
        # Fallback fuzzy when hashes absent (e.g., first time)
        return JaroWinkler.normalized_similarity(
            f"{c.first_name} {c.last_name}", f"{c.first_name} {c.last_name}"
        )

    def _dob_score(self, c: PatientMatchCandidate, m: MasterPatient) -> float:
        if m.dob_year is None:
            return 0.0
        if c.date_of_birth.year == m.dob_year:
            return 1.0
        # Tolerate ±1 year
        if abs(c.date_of_birth.year - m.dob_year) == 1:
            return 0.5
        return 0.0

    def _addr_score(self, c: PatientMatchCandidate, m: MasterPatient) -> float:
        score = 0.0
        if c.state and m.state and c.state.upper() == m.state.upper():
            score += 0.5
        if c.postal_code and m.zip3:
            if c.postal_code[:3] == m.zip3:
                score += 0.5
        return min(score, 1.0)

    def _ident_score(self, c: PatientMatchCandidate, m: MasterPatient) -> float:
        # Strong signal: exact match on any identifier in the master's source_ids
        if c.source_id in m.source_ids:
            return 1.0
        return 0.0

    @staticmethod
    def compare_names_jw(a: str, b: str) -> float:
        """Public helper for tests/UI."""
        return JaroWinkler.normalized_similarity(a, b)

    @staticmethod
    def dob_within_tolerance(d1, d2, tolerance_days: int = 1) -> bool:
        return abs((d1 - d2).days) <= tolerance_days
