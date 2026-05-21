"""Claims adjudication — reconciles EDI 837 claims with EDI 835 remittances."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from clinical_etl.config import get_logger
from clinical_etl.models import Claim, RemittanceAdvice

logger = get_logger(__name__)


class ClaimsAdjudicator:
    """Reconciles claims with remittance advice and computes financial KPIs."""

    def adjudicate(
        self, claim: Claim, remittance: RemittanceAdvice
    ) -> dict[str, Decimal | bool | list]:
        """Compare claim against remittance, return adjudication result."""
        if claim.claim_id != remittance.claim_id:
            raise ValueError(
                f"Claim/Remittance mismatch: {claim.claim_id} vs {remittance.claim_id}"
            )

        billed = claim.total_charges
        paid = remittance.provider_paid
        patient_resp = remittance.patient_responsibility
        adjustment = remittance.contractual_adjustment
        denied = remittance.denied_amount

        reconciled = (paid + patient_resp + adjustment + denied) == billed
        denial_rate = denied / billed if billed > 0 else Decimal("0")

        result = {
            "claim_id": claim.claim_id,
            "billed_amount": billed,
            "paid_amount": paid,
            "patient_responsibility": patient_resp,
            "contractual_adjustment": adjustment,
            "denied_amount": denied,
            "denial_rate": denial_rate,
            "reconciled": reconciled,
            "denial_reasons": remittance.denial_reasons,
            "adjudicated_at": datetime.utcnow(),
        }
        if not reconciled:
            logger.warning(
                "claim_reconciliation_failed",
                claim_id=claim.claim_id,
                billed=str(billed),
                sum_components=str(paid + patient_resp + adjustment + denied),
            )
        return result
