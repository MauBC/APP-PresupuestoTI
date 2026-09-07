from dataclasses import replace
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from database.persistence.batch_builder import (
    build_persistence_batch,
)
from database.persistence.contract import (
    STAGING_COLUMNS,
)
from database.persistence.staging_builder import (
    StagingBuildError,
    build_staging_rows,
)


pytestmark = pytest.mark.unit


CREATED_AT = datetime(
    2026,
    9,
    7,
    15,
    0,
    tzinfo=timezone.utc,
)

STAGED_AT = datetime(
    2026,
    9,
    7,
    15,
    1,
    tzinfo=timezone.utc,
)


def make_row(
    *,
    row_id="row-1",
    version=1,
):
    row = {
        "row_id": row_id,
        "version": version,
        "habilitado": True,
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal(
            "0.00"
        )

    row[
        "enero_usd"
    ] = Decimal("100.00")

    row[
        "marzo_usd"
    ] = None

    row[
        "anio_usd"
    ] = Decimal("100.00")

    return row


def build_batch(
    workspace,
):
    return build_persistence_batch(
        workspace,
        actor="usuario@empresa.com",
        app_version="0.5.0",
        timestamp=CREATED_AT,
        batch_id_factory=lambda: (
            "batch-001"
        ),
    )


def test_staging_contains_complete_editable_state():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                row_id="persistent-1",
                version=5,
            )
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("150.00"),
    )

    batch = build_batch(
        workspace
    )

    rows = build_staging_rows(
        batch,
        timestamp=STAGED_AT,
    )

    assert len(rows) == 1

    record = rows[0].as_record()

    assert tuple(
        record
    ) == STAGING_COLUMNS

    assert record[
        "batch_id"
    ] == "batch-001"

    assert record[
        "row_id"
    ] == "persistent-1"

    assert record[
        "expected_version"
    ] == 5

    assert record[
        "enero_usd"
    ] == Decimal("150.00")

    assert record[
        "anio_usd"
    ] == Decimal("150.00")

    assert record[
        "marzo_usd"
    ] is None

    assert record[
        "habilitado"
    ] is True

    assert record[
        "staged_at"
    ] == STAGED_AT


def test_staging_never_contains_session_row_id():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row()
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("125.00"),
    )

    batch = build_batch(
        workspace
    )

    record = (
        build_staging_rows(
            batch
        )[0]
        .as_record()
    )

    assert (
        "_session_row_id"
        not in record
    )


def test_multiple_changed_rows_create_multiple_staging_rows():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                row_id="row-a"
            ),
            make_row(
                row_id="row-b"
            ),
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("110.00"),
    )

    workspace.edit_month(
        1,
        "enero_usd",
        Decimal("120.00"),
    )

    batch = build_batch(
        workspace
    )

    rows = build_staging_rows(
        batch
    )

    assert len(rows) == 2

    assert {
        row.row_id
        for row in rows
    } == {
        "row-a",
        "row-b",
    }

    assert {
        row.batch_id
        for row in rows
    } == {
        "batch-001"
    }


def test_non_pending_batch_is_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row()
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("125.00"),
    )

    batch = build_batch(
        workspace
    )

    applied_batch = replace(
        batch,
        status="APPLIED",
    )

    with pytest.raises(
        StagingBuildError,
        match="PENDING",
    ):
        build_staging_rows(
            applied_batch
        )


def test_naive_staging_timestamp_is_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row()
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("125.00"),
    )

    batch = build_batch(
        workspace
    )

    with pytest.raises(
        StagingBuildError,
        match="zona horaria",
    ):
        build_staging_rows(
            batch,
            timestamp=datetime(
                2026,
                9,
                7,
                15,
                1,
            ),
        )
