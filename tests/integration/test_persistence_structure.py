import pytest

from app.config.settings import settings
from app.services.bigquery_service import (
    BigQueryService,
)


pytestmark = pytest.mark.integration


def table_ref(
    table_name,
):
    return (
        f"{settings.GOOGLE_CLOUD_PROJECT}."
        f"{settings.BIGQUERY_DATASET}."
        f"{table_name}"
    )


def test_main_table_has_valid_persistence_data():
    service = BigQueryService()

    ref = service.get_table_reference()

    sql = f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(row_id) AS row_ids,
            COUNT(DISTINCT row_id)
                AS distinct_row_ids,

            COUNTIF(row_id IS NULL)
                AS null_row_ids,

            COUNTIF(habilitado IS NULL)
                AS null_habilitado,

            COUNTIF(version IS NULL)
                AS null_version,

            COUNTIF(version < 1)
                AS invalid_version,

            COUNTIF(created_at IS NULL)
                AS null_created_at,

            COUNTIF(created_by IS NULL)
                AS null_created_by,

            COUNTIF(updated_at IS NULL)
                AS null_updated_at,

            COUNTIF(updated_by IS NULL)
                AS null_updated_by

        FROM `{ref}`
    """

    row = next(
        service.client
        .query(sql)
        .result()
    )

    assert row.total_rows > 0

    assert (
        row.row_ids
        == row.total_rows
    )

    assert (
        row.distinct_row_ids
        == row.total_rows
    )

    assert row.null_row_ids == 0
    assert row.null_habilitado == 0
    assert row.null_version == 0
    assert row.invalid_version == 0
    assert row.null_created_at == 0
    assert row.null_created_by == 0
    assert row.null_updated_at == 0
    assert row.null_updated_by == 0


@pytest.mark.parametrize(
    "table_name",
    (
        settings.BIGQUERY_BATCH_TABLE,
        settings.BIGQUERY_AUDIT_TABLE,
        settings.BIGQUERY_STAGING_TABLE,
    ),
)
def test_persistence_support_table_exists(
    table_name,
):
    service = BigQueryService()

    table = service.client.get_table(
        table_ref(
            table_name
        )
    )

    assert table is not None