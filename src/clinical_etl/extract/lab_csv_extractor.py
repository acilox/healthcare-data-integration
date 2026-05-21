"""Lab vendor CSV extractor."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterator

import pandas as pd

from clinical_etl.config import get_logger
from clinical_etl.models import PatientMatchCandidate, PatientSource

logger = get_logger(__name__)


REQUIRED_COLUMNS = {"patient_id", "first_name", "last_name", "dob"}


class LabCSVExtractor:
    """Parses lab vendor CSVs into PatientMatchCandidate records."""

    def extract(self, csv_path: str | Path) -> Iterator[PatientMatchCandidate]:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Lab CSV not found: {path}")

        df = pd.read_csv(path, parse_dates=["dob"])
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns in {path.name}: {missing}")

        logger.info("lab_csv_loaded", file=str(path), rows=len(df))

        for _, row in df.iterrows():
            try:
                yield PatientMatchCandidate(
                    source=PatientSource.LAB_CSV,
                    source_id=str(row["patient_id"]),
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    date_of_birth=row["dob"].date(),
                    gender=row.get("gender"),
                    email=row.get("email"),
                    phone=row.get("phone"),
                    postal_code=row.get("zip"),
                    state=row.get("state"),
                    extracted_at=datetime.utcnow(),
                )
            except Exception as e:
                logger.warning("lab_row_invalid", error=str(e))
