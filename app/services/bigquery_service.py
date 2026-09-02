from google.cloud import bigquery

from app.config.settings import settings


class BigQueryService:
    def __init__(self):
        self._client = None

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

        return next(result).connection_test == 1

    def get_table_reference(self) -> str:
        project = settings.GOOGLE_CLOUD_PROJECT
        dataset = settings.BIGQUERY_DATASET
        table = settings.BIGQUERY_TABLE

        if not project or not dataset or not table:
            raise ValueError(
                "La configuracion de BigQuery esta incompleta."
            )

        return f"{project}.{dataset}.{table}"
