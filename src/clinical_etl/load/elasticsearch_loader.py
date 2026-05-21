"""Elasticsearch loader for patient/encounter search indices."""

from __future__ import annotations

from typing import Iterable

from clinical_etl.config import get_logger, get_settings

logger = get_logger(__name__)


class ElasticsearchLoader:
    """Bulk-loads documents into Elasticsearch indices."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, *_):
        if self._client is not None:
            self._client.close()

    def _connect(self) -> None:
        try:
            from elasticsearch import Elasticsearch  # type: ignore[import-not-found]
        except ImportError as e:
            raise RuntimeError("elasticsearch not installed") from e

        self._client = Elasticsearch(
            hosts=[self.settings.es_hosts],
            basic_auth=(
                self.settings.es_user,
                self.settings.es_password.get_secret_value(),
            )
            if self.settings.es_password.get_secret_value() not in ("", "__PLACEHOLDER__")
            else None,
        )
        logger.info("es_connected", hosts=self.settings.es_hosts)

    def bulk_index(self, index: str, docs: Iterable[dict], id_field: str = "master_id") -> int:
        """Bulk index documents using the helpers API."""
        try:
            from elasticsearch.helpers import bulk  # type: ignore[import-not-found]
        except ImportError as e:
            raise RuntimeError("elasticsearch helpers not available") from e

        if self._client is None:
            self._connect()
        assert self._client is not None

        actions = (
            {
                "_index": index,
                "_id": doc.get(id_field),
                "_source": doc,
            }
            for doc in docs
        )
        success, failed = bulk(self._client, actions, raise_on_error=False)
        logger.info("es_bulk_indexed", index=index, success=success, failed=len(failed) if isinstance(failed, list) else 0)
        return success
