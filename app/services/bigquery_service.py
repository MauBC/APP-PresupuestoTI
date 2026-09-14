from threading import Lock
from time import monotonic

from google.cloud import bigquery

from app.config.settings import settings


class BigQueryService:
    _table_cache = {}
    _table_cache_lock = Lock()

    TABLE_CACHE_TTL_SECONDS = 300.0

    def __init__(self, client=None):
        self._client = client

        # Clientes inyectados se usan
        # principalmente en tests o
        # escenarios aislados y no deben
        # compartir metadata global.
        self._shared_table_cache_enabled = (
            client is None
        )

    @property
    def client(self):
        if self._client is None:
            self._client = bigquery.Client(
                project=settings.GOOGLE_CLOUD_PROJECT or None
            )

        return self._client

    def test_connection(self) -> bool:
        query = "SELECT 1 AS connection_test"

        result = self.client.query(query).result()
        row = next(result)

        return row.connection_test == 1

    def get_table_reference(
        self,
        table_name: str | None = None,
    ) -> str:
        project = settings.GOOGLE_CLOUD_PROJECT
        dataset = settings.BIGQUERY_DATASET

        table = str(
            table_name
            if table_name is not None
            else settings.BIGQUERY_TABLE
        ).strip()

        if (
            not project
            or not dataset
            or not table
        ):
            raise ValueError(
                "La configuracion de BigQuery esta incompleta."
            )

        return (
            f"{project}."
            f"{dataset}."
            f"{table}"
        )

    def get_table(
        self,
        table_name: str | None = None,
    ):
        return self.client.get_table(
            self.get_table_reference(
                table_name
            )
        )

    def get_cached_table(
        self,
        table_name: str | None = None,
    ):
        if not self._shared_table_cache_enabled:
            return self.get_table(
                table_name
            )

        table_ref = (
            self.get_table_reference(
                table_name
            )
        )

        now = monotonic()
        cls = type(self)

        with cls._table_cache_lock:
            cached = cls._table_cache.get(
                table_ref
            )

            if cached is not None:
                cached_at, table = cached

                if (
                    now - cached_at
                    < cls.TABLE_CACHE_TTL_SECONDS
                ):
                    return table

                cls._table_cache.pop(
                    table_ref,
                    None,
                )

        table = self.client.get_table(
            table_ref
        )

        with cls._table_cache_lock:
            cls._table_cache[
                table_ref
            ] = (
                monotonic(),
                table,
            )

        return table

    @classmethod
    def clear_table_cache(
        cls,
    ):
        with cls._table_cache_lock:
            cls._table_cache.clear()

    def get_sample_rows(self, limit: int = 5) -> list[dict]:
        if limit < 1:
            raise ValueError(
                "El limite debe ser mayor que cero."
            )

        table = self.get_table()

        rows = self.client.list_rows(
            table,
            max_results=limit,
        )

        return [
            dict(row.items())
            for row in rows
        ]
