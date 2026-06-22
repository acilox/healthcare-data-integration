"""HIPAA audit logger — immutable append-only log of all PHI accesses."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from clinical_etl.config import get_logger, get_settings

logger = get_logger(__name__)


class HIPAAAuditLogger:
    """Append-only JSONL audit log.

    Every event captures:
      - timestamp (ISO 8601 UTC)
      - actor (user/system identifier)
      - action (READ | WRITE | DELETE | MASK | MATCH)
      - resource_type (Patient | Encounter | Claim | ...)
      - resource_id
      - purpose (TREATMENT | PAYMENT | OPERATIONS | RESEARCH)
      - source (FHIR | ORACLE_EHR | LAB_CSV | EDI_837 | MANUAL)
      - metadata (free-form dict)
    """

    def __init__(self) -> None:
        s = get_settings()
        self.path = Path(s.audit_log_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        purpose: str,
        source: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        event = {
            "ts": datetime.now(tz=UTC).isoformat(),
            "actor": actor,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "purpose": purpose,
            "source": source,
            "metadata": metadata or {},
            "pid": os.getpid(),
        }
        # Append-only mode
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        logger.debug("hipaa_audit", **event)
