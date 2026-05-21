"""EDI 837/835 X12 extractor (simplified parser for demo purposes).

A production implementation would use `pyx12` or `bots` for full X12 parsing.
This module includes a minimal parser sufficient to demonstrate the data flow.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterator

from clinical_etl.config import get_logger
from clinical_etl.models import Claim, ClaimLine, RemittanceAdvice

logger = get_logger(__name__)


class EDIExtractor:
    """Parses EDI 837 (claims) and 835 (remittance) files."""

    def parse_837(self, file_path: str | Path) -> Iterator[Claim]:
        """Parse an EDI 837 claim file. Demo implementation reads segments split by ~."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(path)
        content = path.read_text()
        segments = [s.strip() for s in content.split("~") if s.strip()]

        # Demo parser: looks for CLM segments — a real X12 parser would use loops.
        for seg in segments:
            parts = seg.split("*")
            if parts[0] == "CLM" and len(parts) >= 6:
                yield Claim(
                    claim_id=parts[1],
                    master_id=f"MPI-{parts[1]}",  # placeholder linkage
                    payer_id="PAYER-001",
                    statement_from=date.today(),
                    statement_to=date.today(),
                    total_charges=Decimal(parts[2]),
                    claim_type="PROFESSIONAL",
                    submitted_at=datetime.utcnow(),
                    lines=[
                        ClaimLine(
                            line_number=1,
                            procedure_code="99213",
                            units=1,
                            charge_amount=Decimal(parts[2]),
                            service_date=date.today(),
                        )
                    ],
                )

    def parse_835(self, file_path: str | Path) -> Iterator[RemittanceAdvice]:
        """Parse an EDI 835 remittance file. Demo implementation."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(path)
        content = path.read_text()
        segments = [s.strip() for s in content.split("~") if s.strip()]

        for seg in segments:
            parts = seg.split("*")
            if parts[0] == "CLP" and len(parts) >= 7:
                billed = Decimal(parts[3])
                paid = Decimal(parts[4])
                pt_resp = Decimal(parts[5])
                adj = billed - paid - pt_resp
                yield RemittanceAdvice(
                    remittance_id=f"REM-{parts[1]}",
                    claim_id=parts[1],
                    payer_id="PAYER-001",
                    payment_method="ACH",
                    payment_amount=paid,
                    payment_date=date.today(),
                    provider_paid=paid,
                    patient_responsibility=pt_resp,
                    contractual_adjustment=adj if adj >= 0 else Decimal("0"),
                    denied_amount=Decimal("0"),
                    received_at=datetime.utcnow(),
                )
