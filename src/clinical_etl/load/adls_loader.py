"""Azure Data Lake Gen2 loader for Delta tables."""

from __future__ import annotations

from typing import Any

import pandas as pd

from clinical_etl.config import get_logger, get_settings

logger = get_logger(__name__)


class ADLSDeltaLoader:
    """Writes pandas DataFrames to ADLS Gen2 as Delta tables.

    Uses `deltalake` for native Delta protocol support.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def _adls_path(self, table_name: str) -> str:
        return (
            f"abfs://{self.settings.azure_container}@"
            f"{self.settings.azure_storage_account}.dfs.core.windows.net/"
            f"{self.settings.azure_blob_prefix}{table_name}"
        )

    def _storage_options(self) -> dict[str, str]:
        return {
            "account_name": self.settings.azure_storage_account,
            "account_key": self.settings.azure_storage_key.get_secret_value(),
        }

    def write_delta(
        self,
        df: pd.DataFrame,
        table_name: str,
        mode: str = "append",
        partition_by: list[str] | None = None,
    ) -> int:
        """Write DataFrame to Delta table on ADLS."""
        if df.empty:
            logger.info("adls_no_data", table=table_name)
            return 0

        try:
            from deltalake.writer import write_deltalake  # type: ignore[import-not-found]
        except ImportError as e:
            raise RuntimeError("deltalake not installed") from e

        path = self._adls_path(table_name)
        write_deltalake(
            path,
            df,
            mode=mode,
            partition_by=partition_by,
            storage_options=self._storage_options(),
        )
        logger.info(
            "adls_delta_written", table=table_name, rows=len(df), mode=mode, path=path
        )
        return len(df)
