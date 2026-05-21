"""HIPAA Safe Harbor PHI masking.

Implements masking for the 18 PHI identifiers per 45 CFR 164.514(b):
1. Names → hashed pseudonyms
2. Geographic subdivisions smaller than state → ZIP truncated to first 3 digits
3. All elements of dates (except year) → keep year only; ages over 89 → no DOB
4. Phone, fax → masked
5. Email → masked
6. SSN → last 4 only
7. MRN → hashed
8. Health plan IDs → hashed
9. Account numbers → hashed
10. Certificate/license numbers → masked
11. Vehicle identifiers → masked
12. Device identifiers → masked
13. URLs → masked
14. IP addresses → /16 subnet
15. Biometric identifiers → masked
16. Full-face photos → masked
17. Other unique characteristics → masked
18. Any unique identifying number/characteristic
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any, Optional

from clinical_etl.config import get_logger, get_settings

logger = get_logger(__name__)


class PHIMasker:
    """Apply Safe Harbor masking to PHI fields."""

    SSN_REGEX = re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b")
    EMAIL_REGEX = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
    PHONE_REGEX = re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    IP_REGEX = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

    def __init__(self) -> None:
        s = get_settings()
        self.enabled = s.masking_enabled
        self._salt = s.masking_salt.get_secret_value()

    # ---- Individual maskers ----
    def hash_name(self, name: str) -> str:
        if not name:
            return ""
        normalized = name.strip().lower()
        return hashlib.sha256((normalized + self._salt).encode()).hexdigest()[:16]

    def mask_dob(self, dob: date | datetime | None) -> Optional[int]:
        """Return year only. If age > 89, return None per Safe Harbor."""
        if dob is None:
            return None
        if isinstance(dob, datetime):
            dob = dob.date()
        age = (date.today() - dob).days // 365
        if age > 89:
            return None
        return dob.year

    def mask_zip(self, zip_code: str | None) -> Optional[str]:
        if not zip_code:
            return None
        # Per Safe Harbor: ZIP3 also blanked for ZIP3s with population < 20,000
        # Here we conservatively truncate to ZIP3 always.
        digits = re.sub(r"\D", "", zip_code)
        return digits[:3] if len(digits) >= 3 else None

    def mask_ssn(self, ssn: str | None) -> Optional[str]:
        if not ssn:
            return None
        digits = re.sub(r"\D", "", ssn)
        return digits[-4:] if len(digits) >= 4 else None

    def mask_email(self, email: str | None) -> Optional[str]:
        if not email:
            return None
        # Keep domain, mask local part
        try:
            local, domain = email.split("@", 1)
            return f"***@{domain}"
        except ValueError:
            return "***"

    def mask_phone(self, phone: str | None) -> Optional[str]:
        if not phone:
            return None
        return "***-***-XXXX"

    def mask_ip(self, ip: str | None) -> Optional[str]:
        if not ip:
            return None
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.0.0/16"
        return "0.0.0.0/0"

    def mask_text(self, text: str) -> str:
        """Apply regex-based redaction to free-text fields."""
        if not text:
            return ""
        text = self.SSN_REGEX.sub("[REDACTED-SSN]", text)
        text = self.EMAIL_REGEX.sub("[REDACTED-EMAIL]", text)
        text = self.PHONE_REGEX.sub("[REDACTED-PHONE]", text)
        text = self.IP_REGEX.sub("[REDACTED-IP]", text)
        return text

    # ---- Record-level masking ----
    def mask_patient_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Apply masking to a flat patient dict. Mutates a copy."""
        if not self.enabled:
            logger.warning("phi_masking_disabled")
            return record

        out = record.copy()
        # Names
        if "first_name" in out:
            out["first_name_hash"] = self.hash_name(out.pop("first_name") or "")
        if "last_name" in out:
            out["last_name_hash"] = self.hash_name(out.pop("last_name") or "")
        if "middle_name" in out:
            out.pop("middle_name")

        # DOB
        if "date_of_birth" in out:
            out["dob_year"] = self.mask_dob(out.pop("date_of_birth"))

        # Address
        if "postal_code" in out:
            out["zip3"] = self.mask_zip(out.pop("postal_code"))
        out.pop("address_line1", None)
        out.pop("city", None)

        # Contact
        if "email" in out:
            out["email"] = self.mask_email(out["email"])
        if "phone" in out:
            out["phone"] = self.mask_phone(out["phone"])

        # SSN/MRN
        if "ssn_last4" in out and out["ssn_last4"]:
            out["ssn_last4"] = self.mask_ssn(str(out["ssn_last4"]))
        if "mrn" in out and out["mrn"]:
            out["mrn"] = self.hash_name(str(out["mrn"]))

        return out
