from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_group_edit_service import (
    PresupuestoGroupEditError,
    PresupuestoGroupEditService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)


pytestmark = pytest.mark.unit


def make_row(
    *,
    gasto,
    pais="PERU",
    categoria="LICENCIAS",
    enero="0.00",
    febrero="0.00",
    enabled=True,
):
    row = {
        "nombre_gasto": gasto,
        "pais": pais,
        "categoria_gasto": categoria,
        "presupuestador": "ANA",
        "habilitado": enabled,
    }

    for month in USD_MONTH_COLUMNS:
        row[month] = Decimal("0.00")

    row["enero_usd"] = Decimal(
        enero
    )

    row["febrero_usd"] = Decimal(
        febrero
    )

    row["anio_usd"] = (
        Decimal(enero)
        + Decimal(febrero)
    )

    return row


def build_workspace():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="A",
                enero="10.00",
                febrero="30.00",
            ),
            make_row(
                gasto="B",
                enero="20.00",
                febrero="40.00",
            ),
        ]
    )

    service = (
        PresupuestoGroupEditService(
            workspace
        )
    )

    return workspace, service


def test_preview_returns_affected_rows():
    _, service = build_workspace()

    preview = service.preview(
        group_columns=("pais",),
        group_values=("PERU",),
        column="anio_usd",
        target_total="200.00",
    )

    assert preview.row_count == 2

    assert (
        preview.current_total
        == Decimal("100.00")
    )

    assert (
        preview.target_total
        == Decimal("200.00")
    )

    assert (
        preview.difference
        == Decimal("100.00")
    )

    assert (
        preview.variation_percent
        == Decimal("100.00")
    )


def test_group_month_edit_is_proportional():
    workspace, service = (
        build_workspace()
    )

    service.apply(
        group_columns=("pais",),
        group_values=("PERU",),
        column="enero_usd",
        target_total="60.00",
    )

    row_a = workspace.get_row(0)
    row_b = workspace.get_row(1)

    assert (
        row_a["enero_usd"]
        == Decimal("20.00")
    )

    assert (
        row_b["enero_usd"]
        == Decimal("40.00")
    )

    assert (
        row_a["anio_usd"]
        == Decimal("50.00")
    )

    assert (
        row_b["anio_usd"]
        == Decimal("80.00")
    )


def test_group_annual_edit_distributes_all_months():
    workspace, service = (
        build_workspace()
    )

    service.apply(
        group_columns=("pais",),
        group_values=("PERU",),
        column="anio_usd",
        target_total="200.00",
    )

    row_a = workspace.get_row(0)
    row_b = workspace.get_row(1)

    assert (
        row_a["enero_usd"]
        == Decimal("20.00")
    )

    assert (
        row_a["febrero_usd"]
        == Decimal("60.00")
    )

    assert (
        row_a["anio_usd"]
        == Decimal("80.00")
    )

    assert (
        row_b["enero_usd"]
        == Decimal("40.00")
    )

    assert (
        row_b["febrero_usd"]
        == Decimal("80.00")
    )

    assert (
        row_b["anio_usd"]
        == Decimal("120.00")
    )

    assert (
        row_a["anio_usd"]
        + row_b["anio_usd"]
        == Decimal("200.00")
    )


def test_disabled_rows_are_excluded():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="A",
                enero="10.00",
                enabled=True,
            ),
            make_row(
                gasto="B",
                enero="20.00",
                enabled=False,
            ),
        ]
    )

    service = (
        PresupuestoGroupEditService(
            workspace
        )
    )

    preview = service.apply(
        group_columns=("pais",),
        group_values=("PERU",),
        column="enero_usd",
        target_total="20.00",
    )

    assert preview.row_count == 1

    assert (
        workspace.get_row(0)[
            "enero_usd"
        ]
        == Decimal("20.00")
    )

    assert (
        workspace.get_row(1)[
            "enero_usd"
        ]
        == Decimal("20.00")
    )


def test_group_edit_creates_one_history_batch():
    workspace, service = (
        build_workspace()
    )

    service.apply(
        group_columns=("pais",),
        group_values=("PERU",),
        column="anio_usd",
        target_total="200.00",
    )

    assert workspace.history_count == 1
    assert workspace.pending_row_count == 2


def test_group_edit_undo_restores_all_rows():
    workspace, service = (
        build_workspace()
    )

    service.apply(
        group_columns=("pais",),
        group_values=("PERU",),
        column="anio_usd",
        target_total="200.00",
    )

    workspace.undo_last()

    row_a = workspace.get_row(0)
    row_b = workspace.get_row(1)

    assert (
        row_a["anio_usd"]
        == Decimal("40.00")
    )

    assert (
        row_b["anio_usd"]
        == Decimal("60.00")
    )

    assert workspace.history_count == 0
    assert workspace.pending_row_count == 0


def test_zero_group_cannot_receive_nonzero_budget():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="A",
            ),
            make_row(
                gasto="B",
            ),
        ]
    )

    service = (
        PresupuestoGroupEditService(
            workspace
        )
    )

    with pytest.raises(
        PresupuestoGroupEditError
    ):
        service.apply(
            group_columns=("pais",),
            group_values=("PERU",),
            column="anio_usd",
            target_total="10000.00",
        )


def test_same_total_does_not_create_history():
    workspace, service = (
        build_workspace()
    )

    preview = service.apply(
        group_columns=("pais",),
        group_values=("PERU",),
        column="anio_usd",
        target_total="100.00",
    )

    assert (
        preview.current_total
        == Decimal("100.00")
    )

    assert workspace.history_count == 0
    assert workspace.pending_row_count == 0