from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from database.persistence.batch_builder import (
    PersistenceBuildError,
    build_persistence_batch,
)


pytestmark = pytest.mark.unit


FIXED_TIME = datetime(
    2026,
    9,
    7,
    15,
    0,
    tzinfo=timezone.utc,
)


def make_row(
    *,
    row_id="row-1",
    version=1,
    enero="100.00",
    febrero="0.00",
):
    row = {
        "row_id": row_id,
        "version": version,
        "habilitado": True,
        "pais": "PERU",
        "nombre_gasto": "Servicio A",
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal(
            "0.00"
        )

    row["enero_usd"] = (
        None
        if enero is None
        else Decimal(enero)
    )

    row["febrero_usd"] = (
        None
        if febrero is None
        else Decimal(febrero)
    )

    row["anio_usd"] = sum(
        (
            value
            for column in USD_MONTH_COLUMNS
            if (
                value := row.get(column)
            ) is not None
        ),
        Decimal("0.00"),
    )

    return row


def build_batch(
    workspace,
):
    return build_persistence_batch(
        workspace,
        actor="usuario@empresa.com",
        app_version="0.5.0",
        timestamp=FIXED_TIME,
        batch_id_factory=lambda: (
            "batch-test"
        ),
    )


def test_month_edit_resolves_real_row_id_and_version():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                row_id="real-row-123",
                version=7,
            )
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

    assert batch.batch_id == (
        "batch-test"
    )

    assert batch.status == "PENDING"

    assert batch.actor == (
        "usuario@empresa.com"
    )

    assert batch.app_version == (
        "0.5.0"
    )

    assert batch.row_count == 1
    assert batch.field_count == 2

    row = batch.rows[0]

    assert row.row_id == (
        "real-row-123"
    )

    assert row.expected_version == 7
    assert row.version_after == 8

    changed_columns = {
        change.column
        for change in row.field_changes
    }

    assert changed_columns == {
        "enero_usd",
        "anio_usd",
    }


def test_disable_creates_boolean_change():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row()
        ]
    )

    workspace.set_enabled(
        0,
        False,
    )

    batch = build_batch(
        workspace
    )

    assert batch.row_count == 1
    assert batch.field_count == 1

    change = (
        batch.rows[0]
        .field_changes[0]
    )

    assert (
        change.column
        == HABILITADO_COLUMN
    )

    assert change.before is True
    assert change.after is False
    assert change.value_type == (
        "BOOLEAN"
    )


def test_annual_edit_counts_all_changed_fields():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                enero="100.00",
                febrero="100.00",
            )
        ]
    )

    workspace.edit_annual(
        0,
        Decimal("300.00"),
    )

    batch = build_batch(
        workspace
    )

    changed_columns = {
        change.column
        for change
        in batch.rows[0].field_changes
    }

    assert changed_columns == {
        "enero_usd",
        "febrero_usd",
        "anio_usd",
    }

    assert batch.field_count == 3


def test_multiple_rows_create_single_batch():
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

    assert batch.batch_id == (
        "batch-test"
    )

    assert batch.row_count == 2
    assert batch.field_count == 4

    assert {
        row.row_id
        for row in batch.rows
    } == {
        "row-a",
        "row-b",
    }


def test_no_pending_changes_is_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row()
        ]
    )

    with pytest.raises(
        PersistenceBuildError,
        match="No existen cambios pendientes",
    ):
        build_batch(
            workspace
        )


def test_missing_row_id_is_rejected():
    workspace = PresupuestoWorkspace()

    row = make_row()

    del row[
        "row_id"
    ]

    workspace.load(
        [row]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("120.00"),
    )

    with pytest.raises(
        PersistenceBuildError,
        match="row_id",
    ):
        build_batch(
            workspace
        )


def test_missing_version_is_rejected():
    workspace = PresupuestoWorkspace()

    row = make_row()

    del row[
        "version"
    ]

    workspace.load(
        [row]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("120.00"),
    )

    with pytest.raises(
        PersistenceBuildError,
        match="version",
    ):
        build_batch(
            workspace
        )


def test_duplicate_persistent_row_id_is_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                row_id="duplicate"
            ),
            make_row(
                row_id="duplicate"
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

    with pytest.raises(
        PersistenceBuildError,
        match="duplicados",
    ):
        build_batch(
            workspace
        )


def test_non_editable_dimension_change_is_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row()
        ]
    )

    replacement = (
        workspace.get_row(0)
    )

    replacement[
        "pais"
    ] = "CHILE"

    workspace.apply_batch(
        description="Cambio invalido",
        replacements={
            0: replacement,
        },
    )

    with pytest.raises(
        PersistenceBuildError,
        match="columna no editable",
    ):
        build_batch(
            workspace
        )


def test_row_id_modified_in_workspace_is_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                row_id="original-id"
            )
        ]
    )

    replacement = (
        workspace.get_row(0)
    )

    replacement[
        "row_id"
    ] = "new-id"

    workspace.apply_batch(
        description="Cambio invalido",
        replacements={
            0: replacement,
        },
    )

    with pytest.raises(
        PersistenceBuildError,
        match="row_id fue modificado",
    ):
        build_batch(
            workspace
        )


def test_version_modified_in_workspace_is_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                version=3
            )
        ]
    )

    replacement = (
        workspace.get_row(0)
    )

    replacement[
        "version"
    ] = 4

    workspace.apply_batch(
        description="Cambio invalido",
        replacements={
            0: replacement,
        },
    )

    with pytest.raises(
        PersistenceBuildError,
        match="version fue modificada",
    ):
        build_batch(
            workspace
        )


def test_empty_actor_is_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row()
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("120.00"),
    )

    with pytest.raises(
        PersistenceBuildError,
        match="actor",
    ):
        build_persistence_batch(
            workspace,
            actor="   ",
            timestamp=FIXED_TIME,
        )


def test_naive_timestamp_is_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row()
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("120.00"),
    )

    with pytest.raises(
        PersistenceBuildError,
        match="zona horaria",
    ):
        build_persistence_batch(
            workspace,
            actor="usuario@empresa.com",
            timestamp=datetime(
                2026,
                9,
                7,
                15,
                0,
            ),
        )
