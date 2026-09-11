from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_group_edit_service import (
    PresupuestoGroupEditService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)


pytestmark = pytest.mark.unit


def make_row(
    *,
    gasto,
    ceco,
    amount,
):
    row = {
        "nombre_gasto": gasto,
        "ceco": ceco,
        "pais": "PERU",
        "presupuestador": "ANA",
        HABILITADO_COLUMN: True,
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal(
            "0.00"
        )

    row["enero_usd"] = Decimal(
        amount
    )

    row["anio_usd"] = Decimal(
        amount
    )

    return row


def build_workspace():
    workspace = (
        PresupuestoWorkspace()
    )

    workspace.load(
        (
            make_row(
                gasto="LICENCIAS",
                ceco="1001",
                amount="100.00",
            ),
            make_row(
                gasto="LICENCIAS",
                ceco="1002",
                amount="200.00",
            ),
            make_row(
                gasto="TELEFONIA",
                ceco="1003",
                amount="300.00",
            ),
        )
    )

    return workspace


def test_group_state_finds_underlying_rows():
    workspace = build_workspace()

    service = (
        PresupuestoGroupEditService(
            workspace
        )
    )

    row_ids = (
        service.get_group_row_ids(
            group_columns=(
                "nombre_gasto",
            ),
            group_values=(
                "LICENCIAS",
            ),
            enabled=True,
        )
    )

    assert row_ids == (
        0,
        1,
    )


def test_disable_group_preserves_amounts():
    workspace = build_workspace()

    service = (
        PresupuestoGroupEditService(
            workspace
        )
    )

    affected = (
        service.set_group_enabled(
            group_columns=(
                "nombre_gasto",
            ),
            group_values=(
                "LICENCIAS",
            ),
            enabled=False,
        )
    )

    assert affected == 2

    assert (
        workspace.get_row(0)[
            HABILITADO_COLUMN
        ]
        is False
    )

    assert (
        workspace.get_row(1)[
            HABILITADO_COLUMN
        ]
        is False
    )

    assert (
        workspace.get_row(2)[
            HABILITADO_COLUMN
        ]
        is True
    )

    assert (
        workspace.get_row(0)[
            "anio_usd"
        ]
        == Decimal("100.00")
    )

    assert (
        workspace.get_row(1)[
            "anio_usd"
        ]
        == Decimal("200.00")
    )

    assert (
        workspace.pending_row_count
        == 2
    )

    assert (
        workspace.history_count
        == 1
    )


def test_disable_group_is_single_undo():
    workspace = build_workspace()

    service = (
        PresupuestoGroupEditService(
            workspace
        )
    )

    service.set_group_enabled(
        group_columns=(
            "nombre_gasto",
        ),
        group_values=(
            "LICENCIAS",
        ),
        enabled=False,
    )

    assert workspace.undo_last()

    assert (
        workspace.get_row(0)[
            HABILITADO_COLUMN
        ]
        is True
    )

    assert (
        workspace.get_row(1)[
            HABILITADO_COLUMN
        ]
        is True
    )

    assert not workspace.has_changes


def test_group_scope_respects_all_dimensions():
    workspace = build_workspace()

    service = (
        PresupuestoGroupEditService(
            workspace
        )
    )

    affected = (
        service.set_group_enabled(
            group_columns=(
                "nombre_gasto",
                "ceco",
            ),
            group_values=(
                "LICENCIAS",
                "1001",
            ),
            enabled=False,
        )
    )

    assert affected == 1

    assert (
        workspace.get_row(0)[
            HABILITADO_COLUMN
        ]
        is False
    )

    assert (
        workspace.get_row(1)[
            HABILITADO_COLUMN
        ]
        is True
    )
