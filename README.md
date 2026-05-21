# healthcare-data-integration

A reference implementation of a healthcare data hub: consolidates
patient data from a FHIR R4 server, a legacy Oracle EHR, lab CSV drops
over SFTP, and EDI 837/835 claim files into a master patient index plus
downstream Delta / Postgres / Elasticsearch stores. Includes
probabilistic record matching, Safe-Harbor PHI masking, and an
immutable HIPAA audit log.

## Problem domain

Patient identifiers fragment across hospital systems — the same person
exists multiple times under slightly different names, dates of birth, or
addresses. Analytical and operational use cases require a single
identity reconciled across sources, with PHI handled correctly under
HIPAA. The patterns here cover that consolidation: fuzzy identity
matching, code validation, masking for analytics paths, and
claim/remittance reconciliation.

## Sources and targets

```
sources                          targets
-------                          -------
FHIR R4 (OAuth client-creds) --> postgres (MPI, encounter ODS)
oracle (legacy EHR)          --> azure data lake (delta)
lab vendor CSVs over SFTP    --> elasticsearch (patient search)
EDI 837 / 835 claims         --> HIPAA audit log (jsonl, append-only)
```

## Layout

```
src/clinical_etl/
  config/        settings + structured logging
  extract/       fhir, oracle_ehr, lab_csv, edi (837/835)
  transform/     matching (rapidfuzz), masking (Safe Harbor 18 ids),
                 code_validator (ICD-10 / CPT), adjudication (837 vs 835)
  load/          adls (deltalake), postgres (upsert), elasticsearch (bulk)
  orchestration/ Celery tasks + beat schedule
  models/        pydantic schemas (Patient, Encounter, Claim, ...)
  utils/         HIPAAAuditLogger
  main.py        CLI (run, demo-fhir)
```

## Matching

Default weights: 0.35 name / 0.30 identifier / 0.25 dob / 0.10 address.
Scores >= 0.85 auto-merge; 0.65 to 0.85 enters a steward queue for human
resolution. Name similarity uses Jaro-Winkler from `rapidfuzz`, chosen
for better recall on nickname pairs than plain Levenshtein.

## PHI masking

`PHIMasker` covers the 18 identifiers from 45 CFR 164.514(b). Outputs
are consistent (salted SHA-256 over normalised text), which lets the
matcher join records by hash. The salt is loaded from environment
configuration and must remain stable once data is persisted to the
warehouse — rotation requires a re-key procedure.

## EDI

The included 837/835 parser is intentionally lightweight (segment-level
parsing of `CLM` / `CLP` records). Production deployments against real
partner files should substitute `pyx12` or `bots`, which handle the full
X12 envelope and edge cases.

## Running locally

```
cp .env.example .env
make install
make docker-up                # postgres, redis, elasticsearch, azurite
make run                      # CLI demo against data/sample/
make celery-worker            # in a second terminal
```

Sample data:

- `data/sample/lab_patients.csv` — 10 rows used by the masker demo
- `data/sample/fhir_patient.json` — one FHIR Patient resource
- `data/sample/sample.837` — a stripped-down 837 envelope

## Stack

Python 3.11, pandas, polars, fhir.resources, hl7apy, pyx12 (optional),
oracledb, psycopg2, deltalake, elasticsearch, rapidfuzz, redis, celery,
pydantic, structlog.

## Design notes

- The audit log is local JSONL by default. Production deployments
  should land it on object storage with write-once semantics
  (S3 Object Lock or ADLS immutability policies).
- The Elasticsearch index is fed from the masked projection. If
  unmasked search is required (e.g. for treatment-purpose queries),
  the unmasked side-store needs a separate role, and every query must
  be captured by the audit logger.
- Celery beat is configured in the task module but not started by
  `make docker-up`. Start it manually with
  `celery -A clinical_etl.orchestration.tasks beat` for scheduled
  ingestion.

## About this code

Open-source companion to the healthcare data work done by
[acilox](https://github.com/acilox). For paid implementation,
deployment, or extension of these patterns — including hardening
against real HIPAA-regulated environments — open an issue.
