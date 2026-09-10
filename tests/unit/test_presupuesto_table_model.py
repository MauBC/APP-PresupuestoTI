from decimal import Decimal

import pytest

from PySide6.QtCore import Qt

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_analysis_service import (
    PresupuestoWorkspaceAnalysisService,
)
from app.ui.models.presupuesto_table_model import (
    PresupuestoTableModel,
)


pytestmark = pytest.mark.unit


def make_row():
    row = {
        "nombre_gasto": "Servicio A",
        "ceco": "1001",
        "pais": "PERU",
        "presupuestador": "ANA",
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal("0.00")

    row["enero_usd"] = Decimal("10.00")
    row["febrero_usd"] = Decimal("30.00")
    row["anio_usd"] = Decimal("40.00")

    return row


def build_model():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [make_row()]
    )

    analysis = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    page = analysis.get_page(
        page_index=0,
        page_size=100,
    )

    model = PresupuestoTableModel(
        workspace
    )

    model.set_page(page)

    return (
        workspace,
        model,
    )


def column_index(
    model,
    column_name,
):
    return model._columns.index(
        column_name
    )


def test_dimension_column_is_read_only():
    _, model = build_model()

    index = model.index(
        0,
        column_index(
            model,
            "nombre_gasto",
        ),
    )

    flags = model.flags(index)

    assert not (
        flags
        & Qt.ItemFlag.ItemIsEditable
    )


def test_usd_column_is_editable():
    _, model = build_model()

    index = model.index(
        0,
        column_index(
            model,
            "enero_usd",
        ),
    )

    flags = model.flags(index)

    assert (
        flags
        & Qt.ItemFlag.ItemIsEditable
    )


def test_month_edit_updates_workspace():
    workspace, model = build_model()

    index = model.index(
        0,
        column_index(
            model,
            "enero_usd",
        ),
    )

    changed = model.setData(
        index,
        "20.00",
        Qt.ItemDataRole.EditRole,
    )

    assert changed is True

    row = workspace.get_row(0)

    assert (
        row["enero_usd"]
        == Decimal("20.00")
    )

    assert (
        row["anio_usd"]
        == Decimal("50.00")
    )


def test_annual_edit_redistributes_months():
    workspace, model = build_model()

    index = model.index(
        0,
        column_index(
            model,
            "anio_usd",
        ),
    )

    changed = model.setData(
        index,
        "80.00",
        Qt.ItemDataRole.EditRole,
    )

    assert changed is True

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


def test_habilitado_is_read_only_in_table():
    workspace, model = build_model()

    index = model.index(
        0,
        column_index(
            model,
            HABILITADO_COLUMN,
        ),
    )

    flags = model.flags(
        index
    )

    assert not (
        flags
        & Qt.ItemFlag.ItemIsUserCheckable
    )

    changed = model.setData(
        index,
        Qt.CheckState.Unchecked,
        Qt.ItemDataRole.CheckStateRole,
    )

    assert changed is False

    assert (
        workspace.get_row(0)[
            HABILITADO_COLUMN
        ]
        is True
    )

def test_negative_amount_is_rejected():
    workspace, model = build_model()

    index = model.index(
        0,
        column_index(
            model,
            "enero_usd",
        ),
    )

    changed = model.setData(
        index,
        "-10.00",
        Qt.ItemDataRole.EditRole,
    )

    assert changed is False

    assert (
        workspace.get_row(0)[
            "enero_usd"
        ]
        == Decimal("10.00")
    )
