"""ICD-10-CM and CPT code validator with reference enrichment."""

from __future__ import annotations

import re

from clinical_etl.config import get_logger
from clinical_etl.models import DiagnosisCode, ProcedureCode

logger = get_logger(__name__)


# ICD-10-CM format:  X##.### or X## (3-7 chars). First char alpha (except U).
ICD10_REGEX = re.compile(r"^[A-TV-Z][0-9][0-9A-Z](?:[0-9A-Z]{0,4})$")
# CPT: 5 digits, OR 4 digits + 1 letter (Category III)
CPT_REGEX = re.compile(r"^(?:\d{5}|\d{4}[A-Z])$")


# Simulated reference table for demos
ICD10_REFERENCE = {
    "I10":  ("Hypertension",                    "CIRCULATORY"),
    "E119": ("Type 2 diabetes",                 "ENDOCRINE"),
    "J45":  ("Asthma",                          "RESPIRATORY"),
    "M545": ("Low back pain",                   "MUSCULOSKELETAL"),
    "R51":  ("Headache",                        "SYMPTOMS"),
    "Z00":  ("Encounter for general exam",      "FACTORS_HEALTH"),
}

CPT_REFERENCE = {
    "99213": "Office visit, established patient (15 min)",
    "99214": "Office visit, established patient (25 min)",
    "93000": "Electrocardiogram, complete",
    "80050": "Comprehensive metabolic panel",
    "85025": "CBC with automated differential",
    "71046": "Chest X-ray, two views",
}


class CodeValidator:
    """Validates and enriches clinical codes against reference data."""

    def validate_icd10(self, code: str) -> DiagnosisCode:
        normalized = code.upper().replace(".", "")
        is_valid = bool(ICD10_REGEX.match(normalized))
        ref = ICD10_REFERENCE.get(normalized)
        if is_valid and ref:
            description, category = ref
            return DiagnosisCode(
                code=normalized,
                description=description,
                category=category,
                is_valid=True,
            )
        return DiagnosisCode(
            code=normalized,
            description=None,
            category=None,
            is_valid=is_valid,
        )

    def validate_cpt(self, code: str) -> ProcedureCode:
        normalized = code.strip().upper()
        is_valid = bool(CPT_REGEX.match(normalized))
        return ProcedureCode(
            code=normalized,
            description=CPT_REFERENCE.get(normalized),
            is_valid=is_valid,
        )

    def validate_batch(
        self, icd_codes: list[str], cpt_codes: list[str]
    ) -> tuple[list[DiagnosisCode], list[ProcedureCode]]:
        diagnoses = [self.validate_icd10(c) for c in icd_codes]
        procedures = [self.validate_cpt(c) for c in cpt_codes]
        invalid_dx = [d for d in diagnoses if not d.is_valid]
        invalid_cpt = [p for p in procedures if not p.is_valid]
        if invalid_dx or invalid_cpt:
            logger.warning(
                "code_validation_failures",
                invalid_icd=len(invalid_dx),
                invalid_cpt=len(invalid_cpt),
            )
        return diagnoses, procedures
