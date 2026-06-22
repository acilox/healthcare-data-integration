"""PostgreSQL ODS (Operational Data Store) loader with upserts."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from clinical_etl.config import get_logger, get_settings

logger = get_logger(__name__)


class PostgresODSLoader:
    """Upserts records into the ODS PostgreSQL database."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.engine = None

    def __enter__(self):
        self.engine = create_engine(self.settings.postgres_url, pool_pre_ping=True, pool_size=5)
        return self

    def __exit__(self, *_):
        if self.engine is not None:
            self.engine.dispose()

    def upsert_master_patients(self, records: Iterable[dict]) -> int:
        """Upsert into the master_patient table on master_id PK."""
        df = pd.DataFrame(list(records))
        if df.empty:
            return 0

        assert self.engine is not None
        with self.engine.begin() as conn:
            from sqlalchemy import MetaData, Table

            meta = MetaData()
            tbl = Table("master_patient", meta, autoload_with=self.engine)

            insert_stmt = pg_insert(tbl).values(df.to_dict(orient="records"))
            update_cols = {
                c.name: getattr(insert_stmt.excluded, c.name)
                for c in tbl.columns
                if c.name not in ("master_id", "first_seen_at")
            }
            stmt = insert_stmt.on_conflict_do_update(index_elements=["master_id"], set_=update_cols)
            result = conn.execute(stmt)

        logger.info("postgres_upserted", rows=result.rowcount)
        return result.rowcount or 0
