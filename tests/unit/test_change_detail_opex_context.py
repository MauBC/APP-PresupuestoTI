from decimal import Decimal

import pytest

from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)
from app.services.presupuesto_change_summary_service import (
    PresupuestoChangeSummaryService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)


pytestmark = pytest.mark.unit


def make_row():
    row = {
        "row_id": "row-1",
        "version": 1,
        "habilitado": True,
        "presupuestador": "ANA",
        "pais": "PERU",
        "compania": "RANSA PERU",
        "proveedor": "MICROSOFT",
        "nombre_gasto": "LICENCIAS OFFICE",
        "ceco": "CECO-100",
    }

    for column in (
        OPEX_MODULE_CONFIG
        .month_columns
    ):
        row[column] = Decimal(
            "0.00"
        )

    row["enero_usd"] = Decimal(
        "100.00"
    )

    row[
        OPEX_MODULE_CONFIG
        .annual_column
    ] = Decimal(
        "100.00"
    )

    return row


def test_opex_detail_columns_have_expected_order():
    assert (
        OPEX_MODULE_CONFIG
        .change_detail_columns
    ) == (
        "presupuestador",
        "pais",
        "compania",
        "proveedor",
        "nombre_gasto",
        "ceco",
    )


def test_change_detail_contains_full_opex_context():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        (
            make_row(),
        )
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("150.00"),
    )

    summary = (
        PresupuestoChangeSummaryService(
            workspace
        ).build()
    )

    detail = next(
        item
        for item in summary.details
        if (
            item.column
            == "enero_usd"
        )
    )

    assert detail.context_map == {
        "presupuestador":
            "ANA",
        "pais":
            "PERU",
        "compania":
            "RANSA PERU",
        "proveedor":
            "MICROSOFT",
        "nombre_gasto":
            "LICENCIAS OFFICE",
        "ceco":
            "CECO-100",
    }
