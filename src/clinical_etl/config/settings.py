"""Clinical ETL settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # Oracle
    oracle_host: str = "ehr.example.com"
    oracle_port: int = 1521
    oracle_service_name: str = "EHRPROD"
    oracle_user: str = "clinical_etl_reader"
    oracle_password: SecretStr = SecretStr("__PLACEHOLDER__")

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "clinical_etl_ods"
    postgres_user: str = "clinical_etl"
    postgres_password: SecretStr = SecretStr("__PLACEHOLDER__")

    # FHIR
    fhir_base_url: str = "https://fhir.example.com/r4"
    fhir_client_id: SecretStr = SecretStr("__PLACEHOLDER__")
    fhir_client_secret: SecretStr = SecretStr("__PLACEHOLDER__")
    # OAuth token endpoint URL (not a secret; the credentials are SecretStr above)
    fhir_token_url: str = "https://fhir.example.com/oauth/token"  # noqa: S105

    # SFTP
    sftp_host: str = "labs-sftp.example.com"
    sftp_port: int = 22
    sftp_user: str = "clinical_etl_etl"
    sftp_key_path: str = "/secrets/sftp_rsa"
    sftp_remote_dir: str = "/inbound/labs"

    # EDI
    edi_inbound_dir: str = "data/raw/edi"
    edi_partner_id: str = "__PLACEHOLDER__"

    # Azure ADLS
    azure_storage_account: str = "clinical_etladls"
    azure_storage_key: SecretStr = SecretStr("__PLACEHOLDER__")
    azure_container: str = "clinical_etl"
    azure_blob_prefix: str = "delta/"

    # Elasticsearch
    es_hosts: str = "http://localhost:9200"
    es_user: str = "elastic"
    es_password: SecretStr = SecretStr("__PLACEHOLDER__")
    es_index_patient: str = "patients"
    es_index_encounter: str = "encounters"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_dlq_key: str = "clinical_etl:dlq"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_time_limit: int = 600

    # Matching
    match_auto_merge_threshold: float = 0.85
    match_review_threshold: float = 0.65
    match_dob_tolerance_days: int = 1

    # Masking
    masking_enabled: bool = True
    masking_rules_path: str = "config/masking_rules.yaml"
    masking_salt: SecretStr = SecretStr("__PLACEHOLDER__")

    # Audit
    audit_log_path: str = "logs/hipaa_audit.jsonl"

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:"
            f"{self.postgres_password.get_secret_value()}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
