-- ============================================================
-- Clinical ETL PostgreSQL ODS schema
-- ============================================================

CREATE TABLE IF NOT EXISTS master_patient (
    master_id           VARCHAR(64) PRIMARY KEY,
    first_name_hash     VARCHAR(64),
    last_name_hash      VARCHAR(64),
    dob_year            INTEGER,
    gender              VARCHAR(16),
    zip3                CHAR(3),
    state               VARCHAR(64),
    country             CHAR(2) DEFAULT 'US',
    source_ids          TEXT[],
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    merged_from         TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_mp_first_name_hash ON master_patient(first_name_hash);
CREATE INDEX IF NOT EXISTS idx_mp_last_name_hash ON master_patient(last_name_hash);
CREATE INDEX IF NOT EXISTS idx_mp_zip3 ON master_patient(zip3);

CREATE TABLE IF NOT EXISTS encounter (
    encounter_id        VARCHAR(64) PRIMARY KEY,
    master_id           VARCHAR(64) REFERENCES master_patient(master_id),
    encounter_type      VARCHAR(32),
    start_datetime      TIMESTAMPTZ,
    end_datetime        TIMESTAMPTZ,
    provider_id         VARCHAR(64),
    facility_id         VARCHAR(64),
    diagnoses_json      JSONB,
    procedures_json     JSONB,
    total_charges       NUMERIC(18, 4),
    source_system       VARCHAR(32),
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hipaa_audit (
    audit_id            BIGSERIAL PRIMARY KEY,
    ts                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor               VARCHAR(128) NOT NULL,
    action              VARCHAR(16) NOT NULL,
    resource_type       VARCHAR(32) NOT NULL,
    resource_id         VARCHAR(128) NOT NULL,
    purpose             VARCHAR(32),
    source              VARCHAR(32),
    metadata_json       JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_actor ON hipaa_audit(actor);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON hipaa_audit(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON hipaa_audit(ts);
