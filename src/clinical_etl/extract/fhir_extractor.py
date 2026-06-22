"""FHIR R4 patient extractor with OAuth2 client credentials flow."""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import date, datetime
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from clinical_etl.config import get_logger, get_settings
from clinical_etl.models import PatientMatchCandidate, PatientSource

logger = get_logger(__name__)


class FHIRPatientExtractor:
    """Pulls Patient resources from a FHIR R4 server."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = httpx.Client(timeout=30.0)
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def __enter__(self) -> FHIRPatientExtractor:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._client.close()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, max=30),
    )
    def _authenticate(self) -> None:
        """OAuth2 client credentials grant."""
        if self._token and self._token_expires_at > time.time() + 30:
            return
        resp = self._client.post(
            self.settings.fhir_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.settings.fhir_client_id.get_secret_value(),
                "client_secret": self.settings.fhir_client_secret.get_secret_value(),
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + payload.get("expires_in", 3600)
        logger.info("fhir_authenticated")

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, max=30),
    )
    def _fetch_page(self, url: str) -> dict[str, Any]:
        self._authenticate()
        resp = self._client.get(
            url,
            headers={"Authorization": f"Bearer {self._token}", "Accept": "application/fhir+json"},
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_patients(
        self, modified_after: datetime | None = None
    ) -> Iterator[PatientMatchCandidate]:
        """Iterate paginated Patient resources."""
        params = ["_count=100"]
        if modified_after:
            params.append(f"_lastUpdated=gt{modified_after.strftime('%Y-%m-%dT%H:%M:%S')}")
        next_url = f"{self.settings.fhir_base_url}/Patient?{'&'.join(params)}"

        page_count = 0
        total = 0
        while next_url:
            page_count += 1
            bundle = self._fetch_page(next_url)
            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})
                try:
                    yield self._to_candidate(resource)
                    total += 1
                except Exception as e:
                    logger.warning("fhir_patient_invalid", error=str(e))
            # Pagination
            next_url = None
            for link in bundle.get("link", []):
                if link.get("relation") == "next":
                    next_url = link.get("url")
                    break

        logger.info("fhir_extract_complete", pages=page_count, total=total)

    @staticmethod
    def _to_candidate(resource: dict[str, Any]) -> PatientMatchCandidate:
        """Map a FHIR Patient resource to our candidate model."""
        names = resource.get("name", [{}])[0]
        given = names.get("given", [""])
        family = names.get("family", "")
        first = given[0] if given else ""
        middle = given[1] if len(given) > 1 else None

        addr = resource.get("address", [{}])[0]
        telecoms = resource.get("telecom", [])
        email = next((t.get("value") for t in telecoms if t.get("system") == "email"), None)
        phone = next((t.get("value") for t in telecoms if t.get("system") == "phone"), None)

        identifiers = resource.get("identifier", [])
        mrn = next(
            (
                i.get("value")
                for i in identifiers
                if i.get("type", {}).get("coding", [{}])[0].get("code") == "MR"
            ),
            None,
        )

        dob_str = resource.get("birthDate")
        dob = date.fromisoformat(dob_str) if dob_str else None
        if dob is None:
            raise ValueError("Patient missing required birthDate")

        return PatientMatchCandidate(
            source=PatientSource.FHIR,
            source_id=resource["id"],
            mrn=mrn,
            first_name=first or "UNKNOWN",
            middle_name=middle,
            last_name=family or "UNKNOWN",
            date_of_birth=dob,
            gender=resource.get("gender"),
            email=email,
            phone=phone,
            address_line1=(addr.get("line", [None])[0] if addr.get("line") else None),
            city=addr.get("city"),
            state=addr.get("state"),
            postal_code=addr.get("postalCode"),
            country=addr.get("country", "US"),
            extracted_at=datetime.utcnow(),
        )
