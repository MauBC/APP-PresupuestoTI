from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from uuid import uuid4

import pytest

from google.cloud import bigquery

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
    USD_COLUMNS,
)
from app.config.settings import settings
from app.services.bigquery_service import (
    BigQueryService,
)
from database.persistence.bigquery_repository import (
    BigQueryPersistenceRepository,
)
from database.persistence.contract import (
    EDITABLE_VALUE_TYPES,
    PENDING_STATUS,
)
from database.persistence.models import (
    PersistenceBatch,
    PersistenceFieldChange,
    PersistenceRowChange,
)
from database.persistence.staging_builder import (
    build_staging_rows,
)


pytestmark = pytest.mark.integration


def query_parameters(
    **values,
):
    parameters = []

    for name, value in values.items():
        if isinstance(value, int):
            field_type = "INT64"
        else:
            field_type = "STRING"

        parameters.append(
            bigquery.ScalarQueryParameter(
                name,
                field_type,
                value,
            )
        )

    return bigquery.QueryJobConfig(
        query_parameters=parameters
    )


def cleanup_test_batch(
    client,
    *,
    batch_id,
):
    project = (
        settings.GOOGLE_CLOUD_PROJECT
    )

    dataset = (
        settings.BIGQUERY_DATASET
    )

    staging_table = (
        settings
        .BIGQUERY_STAGING_TABLE
    )

    audit_table = (
        settings
        .BIGQUERY_AUDIT_TABLE
    )

    batch_table = (
        settings
        .BIGQUERY_BATCH_TABLE
    )

    config = query_parameters(
        batch_id=batch_id
    )

    statements = (
        f"""
        DELETE FROM
            `{project}.{dataset}.{staging_table}`
        WHERE batch_id = @batch_id
        """,
        f"""
        DELETE FROM
            `{project}.{dataset}.{audit_table}`
        WHERE batch_id = @batch_id
        """,
        f"""
        DELETE FROM
            `{project}.{dataset}.{batch_table}`
        WHERE batch_id = @batch_id
        """,
    )

    for sql in statements:
        client.query(
            sql,
            job_config=config,
            location=(
                settings
                .BIGQUERY_LOCATION
            ),
        ).result()


def count_batch_rows(
    client,
    *,
    batch_id,
):
    table_id = (
        f"{settings.GOOGLE_CLOUD_PROJECT}."
        f"{settings.BIGQUERY_DATASET}."
        f"{settings.BIGQUERY_BATCH_TABLE}"
    )

    sql = f"""
        SELECT
            COUNT(*) AS row_count
        FROM `{table_id}`
        WHERE batch_id = @batch_id
    """

    config = query_parameters(
        batch_id=batch_id
    )

    rows = (
        client.query(
            sql,
            job_config=config,
            location=(
                settings
                .BIGQUERY_LOCATION
            ),
        )
        .result()
    )

    return int(
        next(iter(rows))[
            "row_count"
        ]
    )


def read_batch(
    client,
    *,
    batch_id,
):
    table_id = (
        f"{settings.GOOGLE_CLOUD_PROJECT}."
        f"{settings.BIGQUERY_DATASET}."
        f"{settings.BIGQUERY_BATCH_TABLE}"
    )

    sql = f"""
        SELECT
            batch_id,
            status,
            actor,
            row_count,
            field_count,
            app_version
        FROM `{table_id}`
        WHERE batch_id = @batch_id
    """

    config = query_parameters(
        batch_id=batch_id
    )

    rows = list(
        client.query(
            sql,
            job_config=config,
            location=(
                settings
                .BIGQUERY_LOCATION
            ),
        )
        .result()
    )

    assert len(rows) == 1

    return rows[0]


def read_staging(
    client,
    *,
    batch_id,
):
    table_id = (
        f"{settings.GOOGLE_CLOUD_PROJECT}."
        f"{settings.BIGQUERY_DATASET}."
        f"{settings.BIGQUERY_STAGING_TABLE}"
    )

    sql = f"""
        SELECT
            batch_id,
            row_id,
            expected_version,
            habilitado,
            enero_usd,
            marzo_usd,
            anio_usd
        FROM `{table_id}`
        WHERE batch_id = @batch_id
    """

    config = query_parameters(
        batch_id=batch_id
    )

    return list(
        client.query(
            sql,
            job_config=config,
            location=(
                settings
                .BIGQUERY_LOCATION
            ),
        )
        .result()
    )


def build_test_batch(
    *,
    batch_id,
    row_id,
):
    editable = []

    for column in (
        (
            HABILITADO_COLUMN,
            *USD_COLUMNS,
        )
    ):
        if (
            column
            == HABILITADO_COLUMN
        ):
            value = True

        elif column == "enero_usd":
            value = Decimal(
                "125.00"
            )

        elif column == "marzo_usd":
            value = None

        elif column == "anio_usd":
            value = Decimal(
                "125.00"
            )

        else:
            value = Decimal(
                "0.00"
            )

        editable.append(
            (
                column,
                value,
            )
        )

    field_changes = (
        PersistenceFieldChange(
            column="enero_usd",
            before=Decimal(
                "100.00"
            ),
            after=Decimal(
                "125.00"
            ),
            value_type=(
                EDITABLE_VALUE_TYPES[
                    "enero_usd"
                ]
            ),
        ),
        PersistenceFieldChange(
            column="anio_usd",
            before=Decimal(
                "100.00"
            ),
            after=Decimal(
                "125.00"
            ),
            value_type=(
                EDITABLE_VALUE_TYPES[
                    "anio_usd"
                ]
            ),
        ),
    )

    row = PersistenceRowChange(
        row_id=row_id,
        expected_version=1,
        field_changes=(
            field_changes
        ),
        editable_values=tuple(
            editable
        ),
    )

    now = datetime.now(
        timezone.utc
    )

    return PersistenceBatch(
        batch_id=batch_id,
        status=PENDING_STATUS,
        actor=(
            "integration-test"
        ),
        created_at=now,
        app_version=(
            settings.APP_VERSION
        ),
        rows=(
            row,
        ),
    )


def test_bigquery_batch_and_staging_roundtrip():
    service = (
        BigQueryService()
    )

    repository = (
        BigQueryPersistenceRepository(
            service.client
        )
    )

    token = uuid4().hex

    batch_id = (
        "integration-"
        + token
    )

    row_id = (
        "integration-row-"
        + token
    )

    cleaned = False

    try:
        batch = build_test_batch(
            batch_id=batch_id,
            row_id=row_id,
        )

        staging = (
            build_staging_rows(
                batch
            )
        )

        #
        # 1. Insert PENDING batch.
        #
        repository.insert_pending_batch(
            batch
        )

        assert (
            count_batch_rows(
                service.client,
                batch_id=batch_id,
            )
            == 1
        )

        stored_batch = read_batch(
            service.client,
            batch_id=batch_id,
        )

        assert (
            stored_batch["status"]
            == "PENDING"
        )

        assert (
            stored_batch["actor"]
            == "integration-test"
        )

        assert (
            stored_batch["row_count"]
            == 1
        )

        assert (
            stored_batch["field_count"]
            == 2
        )

        #
        # 2. Retry same batch insert.
        #
        repository.insert_pending_batch(
            batch
        )

        assert (
            count_batch_rows(
                service.client,
                batch_id=batch_id,
            )
            == 1
        )

        #
        # 3. Bulk staging load.
        #
        loaded = (
            repository
            .replace_staging_rows(
                staging
            )
        )

        assert loaded == 1

        assert (
            repository
            .count_staging_rows(
                batch_id
            )
            == 1
        )

        stored_staging = (
            read_staging(
                service.client,
                batch_id=batch_id,
            )
        )

        assert len(
            stored_staging
        ) == 1

        stored = (
            stored_staging[0]
        )

        assert (
            stored["row_id"]
            == row_id
        )

        assert (
            stored[
                "expected_version"
            ]
            == 1
        )

        assert (
            stored[
                "habilitado"
            ]
            is True
        )

        assert (
            stored[
                "enero_usd"
            ]
            == Decimal(
                "125.00"
            )
        )

        assert (
            stored[
                "marzo_usd"
            ]
            is None
        )

        assert (
            stored[
                "anio_usd"
            ]
            == Decimal(
                "125.00"
            )
        )

        #
        # 4. Retry staging.
        #
        loaded_again = (
            repository
            .replace_staging_rows(
                staging
            )
        )

        assert loaded_again == 1

        assert (
            repository
            .count_staging_rows(
                batch_id
            )
            == 1
        )

        #
        # 5. Explicit cleanup.
        #
        cleanup_test_batch(
            service.client,
            batch_id=batch_id,
        )

        cleaned = True

        assert (
            repository
            .count_staging_rows(
                batch_id
            )
            == 0
        )

        assert (
            count_batch_rows(
                service.client,
                batch_id=batch_id,
            )
            == 0
        )

    finally:
        if not cleaned:
            cleanup_test_batch(
                service.client,
                batch_id=batch_id,
            )
