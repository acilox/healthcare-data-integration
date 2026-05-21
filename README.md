# healthcare-data-integration

ETL that consolidates patient data from a FHIR R4 server, a legacy Oracle
EHR, lab CSV drops, and EDI 837/835 claim files into a single master
patient index and downstream Delta/Postgres/Elasticsearch stores. Includes
probabilistic record matching and Safe-Harbor PHI masking.

## Problem

The same person tends to exist 4-5 times across hospital systems with
slightly different names, DOBs or addresses. Joining anything analytical
is impossible without a master patient index (MPI). This project builds
that MPI, masks PHI for the analytics path, and keeps a HIPAA audit trail
of every PHI access.

## Sources & targets

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

The default weights are 0.35 name / 0.30 identifier / 0.25 dob / 0.10
address. Anything >= 0.85 is auto-merged; 0.65-0.85 lands in a steward
queue for a human to resolve. The name comparison runs Jaro-Winkler from
`rapidfuzz`, which gave us materially better recall on nickname pairs
than Levenshtein alone.

## PHI masking

The `PHIMasker` covers the 18 identifiers from 45 CFR 164.514(b). The
output is consistent (salted SHA-256 over normalised text), so the
matcher can still join records by hash. The salt comes from `.env` and
must not change between runs once data is in the warehouse — there's a
TODO to add a key-rotation procedure.

## EDI

The included 837/835 parser is intentionally lightweight (split on `~`
and `*`, look for `CLM` / `CLP` segments). Anything close to production
should swap it for `pyx12` or `bots` — these are unforgiving formats and
real partner files will hit edges this code doesn't cover.

## Running locally

```
cp .env.example .env
make install
make docker-up                # postgres, redis, elasticsearch, azurite
make run                      # CLI demo against data/sample/
make celery-worker            # in a second terminal
```

Sample data:

- `data/sample/lab_patients.csv` — 10 rows the masker walks through
- `data/sample/fhir_patient.json` — one FHIR Patient resource
- `data/sample/sample.837` — a stripped-down 837 envelope

## Stack

Python 3.11, pandas, polars, fhir.resources, hl7apy, pyx12 (planned),
oracledb, psycopg2, deltalake, elasticsearch, rapidfuzz, redis, celery,
pydantic, structlog.

## Caveats

- The audit log is local JSONL in dev. In production it has to land in
  object storage with write-once (S3 object lock or ADLS immutability).
- The ES index is fed from the masked view. If you ever need to search
  by real name, you'll need to grant a separate role to the unmasked
  side-store (and audit every query).
- Celery beat is configured but not running by default — kick it off
  with `celery -A clinical_etl.orchestration.tasks beat` once the
  worker is up.
