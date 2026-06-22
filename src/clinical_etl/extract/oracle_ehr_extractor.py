"""Legacy Oracle EHR extractor."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

from clinical_etl.config import get_logger, get_settings
from clinical_etl.models import PatientMatchCandidate, PatientSource

logger = get_logger(__name__)


PATIENT_QUERY = """
SELECT
    pat_id, mrn, first_name, last_name, dob, gender, email, phone,
    address_line1, city, state, zip, country, last_updated
FROM ehr_legacy.patient
WHERE last_updated > :watermark
"""


class OracleEHRExtractor:
    """Reads patient master from a legacy Oracle EHR schema."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._conn = None

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, *_):
        self.close()

    def _connect(self) -> None:
        try:
            import oracledb  # type: ignore[import-not-found]
        except ImportError as e:
            raise RuntimeError("oracledb driver not installed") from e
        s = self.settings
        self._conn = oracledb.connect(
            user=s.oracle_user,
            password=s.oracle_password.get_secret_value(),
            dsn=f"{s.oracle_host}:{s.oracle_port}/{s.oracle_service_name}",
        )
        logger.info("oracle_ehr_connected")

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def extract(self, watermark: datetime) -> Iterator[PatientMatchCandidate]:
        if self._conn is None:
            self._connect()
        assert self._conn is not None
        cur = self._conn.cursor()
        cur.execute(PATIENT_QUERY, watermark=watermark)
        for row in cur:
            try:
                yield PatientMatchCandidate(
                    source=PatientSource.ORACLE_EHR,
                    source_id=str(row[0]),
                    mrn=row[1],
                    first_name=row[2],
                    last_name=row[3],
                    date_of_birth=row[4],
                    gender=row[5],
                    email=row[6],
                    phone=row[7],
                    address_line1=row[8],
                    city=row[9],
                    state=row[10],
                    postal_code=row[11],
                    country=row[12] or "US",
                    extracted_at=datetime.utcnow(),
                )
            except Exception as e:
                logger.warning("oracle_ehr_row_skip", error=str(e))
        cur.close()
