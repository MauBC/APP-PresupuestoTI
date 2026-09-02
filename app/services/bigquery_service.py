from google.cloud import bigquery

from app.config.settings import settings


class BigQueryService:
    def __init__(self, client=None):
        self._client = client

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

    def get_table_reference(self) -> str:
        project = settings.GOOGLE_CLOUD_PROJECT
        dataset = settings.BIGQUERY_DATASET
        table = settings.BIGQUERY_TABLE

        if not project or not dataset or not table:
            raise ValueError(
                "La configuracion de BigQuery esta incompleta."
            )

        return f"{project}.{dataset}.{table}"

    def get_table(self):
        return self.client.get_table(
            self.get_table_reference()
        )

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
