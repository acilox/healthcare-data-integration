"""Celery task definitions for Clinical ETL.

Run with:
    celery -A clinical_etl.orchestration.tasks worker --loglevel=INFO
"""

from __future__ import annotations

from datetime import datetime

from celery import Celery
from celery.schedules import crontab

from clinical_etl.config import configure_logging, get_logger, get_settings

settings = get_settings()
configure_logging(level=settings.log_level, fmt=settings.log_format)

logger = get_logger(__name__)

app = Celery(
    "clinical_etl",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_time_limit=settings.celery_task_time_limit,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Scheduled (Celery Beat) example schedule
app.conf.beat_schedule = {
    "extract-fhir-hourly": {
        "task": "clinical_etl.orchestration.tasks.extract_fhir_patients",
        "schedule": crontab(minute=0),  # top of every hour
    },
    "extract-edi-daily": {
        "task": "clinical_etl.orchestration.tasks.process_edi_files",
        "schedule": crontab(minute=30, hour=2),  # 02:30 UTC daily
    },
}


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def extract_fhir_patients(self, modified_after: str | None = None):
    """Extract patients from FHIR, match against MPI, mask, load."""
    from clinical_etl.extract import FHIRPatientExtractor
    from clinical_etl.transform import PHIMasker
    from clinical_etl.utils import HIPAAAuditLogger

    audit = HIPAAAuditLogger()
    masker = PHIMasker()

    after = datetime.fromisoformat(modified_after) if modified_after else None
    count = 0
    try:
        with FHIRPatientExtractor() as ext:
            for candidate in ext.fetch_patients(modified_after=after):
                audit.log(
                    actor="clinical_etl_etl",
                    action="READ",
                    resource_type="Patient",
                    resource_id=candidate.source_id,
                    purpose="OPERATIONS",
                    source="FHIR",
                )
                masker.mask_patient_record(candidate.model_dump())
                count += 1
                # In real impl: bulk-buffer and load to ADLS/Postgres/ES
        logger.info("celery_fhir_complete", count=count)
        return count
    except Exception as e:
        logger.exception("celery_fhir_failed", error=str(e))
        raise self.retry(exc=e) from e


@app.task(bind=True, max_retries=3)
def process_edi_files(self):
    """Parse pending EDI 837/835 files and reconcile."""
    from pathlib import Path

    from clinical_etl.extract import EDIExtractor

    ext = EDIExtractor()

    inbox = Path(settings.edi_inbound_dir)
    processed = 0
    if not inbox.exists():
        logger.info("edi_inbox_empty")
        return 0

    for file_path in inbox.glob("*.837"):
        for _claim in ext.parse_837(file_path):
            # In real impl: look up matching 835, then adjudicate
            processed += 1

    logger.info("celery_edi_complete", count=processed)
    return processed
