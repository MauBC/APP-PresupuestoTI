from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_workspace import (
    SESSION_ROW_ID,
    PresupuestoWorkspace,
    PresupuestoWorkspaceError,
)


pytestmark = pytest.mark.unit


def make_row(
    *,
    gasto="Servicio A",
    enero="10.00",
    febrero="30.00",
    annual="40.00",
):
    row = {
        "nombre_gasto": gasto,
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal("0.00")

    row["enero_usd"] = Decimal(enero)
    row["febrero_usd"] = Decimal(febrero)
    row["anio_usd"] = Decimal(annual)

    return row


def test_load_assigns_session_ids():
    workspace = PresupuestoWorkspace()

    source = [
        make_row(
            gasto="Servicio A"
        ),
        make_row(
            gasto="Servicio B"
        ),
    ]

    workspace.load(source)

    assert workspace.is_loaded
    assert workspace.row_count == 2

    assert (
        workspace.get_row(0)[
            SESSION_ROW_ID
        ]
        == 0
    )

    assert (
        workspace.get_row(1)[
            SESSION_ROW_ID
        ]
        == 1
    )


def test_load_does_not_modify_source_rows():
    workspace = PresupuestoWorkspace()

    source_row = make_row()

    workspace.load(
        [source_row]
    )

    assert (
        SESSION_ROW_ID
        not in source_row
    )


def test_load_preserves_original_annual_value():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                annual="40.04"
            )
        ]
    )

    row = workspace.get_row(0)

    assert (
        row["anio_usd"]
        == Decimal("40.04")
    )

    assert (
        row["enero_usd"]
        == Decimal("10.00")
    )

    assert (
        row["febrero_usd"]
        == Decimal("30.00")
    )


def test_edit_month_changes_working_only():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                annual="40.04"
            )
        ]
    )

    changed = workspace.edit_month(
        0,
        "enero_usd",
        Decimal("20.00"),
    )

    working = workspace.get_row(0)
    original = workspace.get_original_row(
        0
    )

    assert changed is True

    assert (
        working["enero_usd"]
        == Decimal("20.00")
    )

    assert (
        working["anio_usd"]
        == Decimal("50.00")
    )

    assert (
        original["enero_usd"]
        == Decimal("10.00")
    )

    assert (
        original["anio_usd"]
        == Decimal("40.04")
    )

    assert workspace.pending_row_count == 1
    assert workspace.has_changes


def test_edit_annual_preserves_distribution():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                annual="40.04"
            )
        ]
    )

    workspace.edit_annual(
        0,
        Decimal("80.00"),
    )

    row = workspace.get_row(0)

    assert (
        row["enero_usd"]
        == Decimal("20.00")
    )

    assert (
        row["febrero_usd"]
        == Decimal("60.00")
    )

    assert (
        row["anio_usd"]
        == Decimal("80.00")
    )


def test_pending_changes_contains_differences():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                annual="40.04"
            )
        ]
    )

    workspace.edit_annual(
        0,
        Decimal("80.00"),
    )

    pending = (
        workspace.get_pending_changes()
    )

    assert len(pending) == 1

    assert (
        pending[0].session_row_id
        == 0
    )

    changed_columns = {
        item.column
        for item in pending[0].changes
    }

    assert "enero_usd" in changed_columns
    assert "febrero_usd" in changed_columns
    assert "anio_usd" in changed_columns


def test_undo_restores_previous_state():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [make_row()]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("20.00"),
    )

    result = workspace.undo_last()

    row = workspace.get_row(0)

    assert result is True

    assert (
        row["enero_usd"]
        == Decimal("10.00")
    )

    assert (
        row["anio_usd"]
        == Decimal("40.00")
    )

    assert workspace.pending_row_count == 0
    assert workspace.history_count == 0
    assert not workspace.has_changes


def test_undo_only_reverts_last_operation():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [make_row()]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("20.00"),
    )

    workspace.edit_month(
        0,
        "febrero_usd",
        Decimal("50.00"),
    )

    workspace.undo_last()

    row = workspace.get_row(0)

    assert (
        row["enero_usd"]
        == Decimal("20.00")
    )

    assert (
        row["febrero_usd"]
        == Decimal("30.00")
    )

    assert (
        row["anio_usd"]
        == Decimal("50.00")
    )

    assert workspace.history_count == 1
    assert workspace.pending_row_count == 1


def test_discard_all_restores_original_rows():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="Servicio A"
            ),
            make_row(
                gasto="Servicio B"
            ),
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("100.00"),
    )

    workspace.edit_month(
        1,
        "febrero_usd",
        Decimal("200.00"),
    )

    assert workspace.pending_row_count == 2

    workspace.discard_all()

    assert (
        workspace.get_row(0)[
            "enero_usd"
        ]
        == Decimal("10.00")
    )

    assert (
        workspace.get_row(1)[
            "febrero_usd"
        ]
        == Decimal("30.00")
    )

    assert workspace.pending_row_count == 0
    assert workspace.history_count == 0
    assert not workspace.has_changes


def test_noop_edit_does_not_create_history():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [make_row()]
    )

    changed = workspace.edit_month(
        0,
        "enero_usd",
        Decimal("10.00"),
    )

    assert changed is False
    assert workspace.history_count == 0
    assert workspace.pending_row_count == 0


def test_invalid_row_id_is_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [make_row()]
    )

    with pytest.raises(
        PresupuestoWorkspaceError
    ):
        workspace.get_row(999)


def test_reload_clears_previous_changes():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [make_row()]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("100.00"),
    )

    assert workspace.has_changes

    workspace.load(
        [
            make_row(
                gasto="Nuevo"
            )
        ]
    )

    assert workspace.row_count == 1
    assert workspace.history_count == 0
    assert workspace.pending_row_count == 0
    assert not workspace.has_changes

    assert (
        workspace.get_row(0)[
            "nombre_gasto"
        ]
        == "Nuevo"
    )