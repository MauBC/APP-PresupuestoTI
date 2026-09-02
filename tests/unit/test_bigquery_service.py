from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.config.settings import settings
from app.services.bigquery_service import BigQueryService


@pytest.mark.unit
def test_table_reference(monkeypatch):
    monkeypatch.setattr(
        settings,
        "GOOGLE_CLOUD_PROJECT",
        "proyecto-test",
    )
    monkeypatch.setattr(
        settings,
        "BIGQUERY_DATASET",
        "dataset_test",
    )
    monkeypatch.setattr(
        settings,
        "BIGQUERY_TABLE",
        "presupuesto_test",
    )

    service = BigQueryService(
        client=MagicMock()
    )

    assert service.get_table_reference() == (
        "proyecto-test.dataset_test.presupuesto_test"
    )


@pytest.mark.unit
def test_connection_success():
    mock_client = MagicMock()

    mock_client.query.return_value.result.return_value = iter(
        [
            SimpleNamespace(
                connection_test=1
            )
        ]
    )

    service = BigQueryService(
        client=mock_client
    )

    assert service.test_connection() is True

    mock_client.query.assert_called_once_with(
        "SELECT 1 AS connection_test"
    )


@pytest.mark.unit
def test_sample_rows_rejects_invalid_limit():
    service = BigQueryService(
        client=MagicMock()
    )

    with pytest.raises(
        ValueError,
        match="mayor que cero",
    ):
        service.get_sample_rows(0)
