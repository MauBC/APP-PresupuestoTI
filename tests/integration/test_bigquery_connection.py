import pytest

from app.config.settings import settings
from app.services.bigquery_service import BigQueryService


pytestmark = pytest.mark.integration


def bigquery_configured() -> bool:
    return all(
        [
            settings.GOOGLE_CLOUD_PROJECT,
            settings.BIGQUERY_DATASET,
            settings.BIGQUERY_TABLE,
        ]
    )


@pytest.mark.skipif(
    not bigquery_configured(),
    reason="BigQuery no esta configurado en .env",
)
def test_bigquery_connection():
    service = BigQueryService()

    assert service.test_connection() is True


@pytest.mark.skipif(
    not bigquery_configured(),
    reason="BigQuery no esta configurado en .env",
)
def test_bigquery_table_exists():
    service = BigQueryService()

    table = service.get_table()

    assert table is not None
    assert table.table_id == settings.BIGQUERY_TABLE


@pytest.mark.skipif(
    not bigquery_configured(),
    reason="BigQuery no esta configurado en .env",
)
def test_bigquery_can_read_sample():
    service = BigQueryService()

    rows = service.get_sample_rows(1)

    assert isinstance(rows, list)
