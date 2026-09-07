from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_change_summary_service import (
    PresupuestoChangeSummaryService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)


pytestmark = pytest.mark.unit


def make_row(
    *,
    pais,
    presupuestador,
    gasto,
    enero,
    febrero,
    habilitado=True,
):
    row = {
        "pais": pais,
        "presupuestador": presupuestador,
        "nombre_gasto": gasto,
        "habilitado": habilitado,
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
                pais="PERU",
                presupuestador="ANA",
                gasto="A",
                enero="10.00",
                febrero="30.00",
            ),
            make_row(
                pais="PERU",
                presupuestador="LUIS",
                gasto="B",
                enero="20.00",
                febrero="40.00",
            ),
        ]
    )

    return workspace


def test_positive_change_updates_total_variation():
    workspace = build_workspace()

    workspace.edit_month(
        0,
        "enero_usd",
        "20.00",
    )

    summary = (
        PresupuestoChangeSummaryService(
            workspace
        ).build()
    )

    assert (
        summary.original_total
        == Decimal("100.00")
    )

    assert (
        summary.simulated_total
        == Decimal("110.00")
    )

    assert (
        summary.difference
        == Decimal("10.00")
    )

    assert (
        summary.variation_percent
        == Decimal("10.00")
    )


def test_country_breakdown_contains_delta():
    workspace = build_workspace()

    workspace.edit_month(
        0,
        "enero_usd",
        "20.00",
    )

    summary = (
        PresupuestoChangeSummaryService(
            workspace
        ).build()
    )

    assert len(
        summary.by_country
    ) == 1

    row = summary.by_country[0]

    assert row.key == "PERU"

    assert (
        row.difference
        == Decimal("10.00")
    )


def test_budgeter_breakdown_separates_changes():
    workspace = build_workspace()

    workspace.edit_month(
        0,
        "enero_usd",
        "20.00",
    )

    workspace.edit_month(
        1,
        "enero_usd",
        "30.00",
    )

    summary = (
        PresupuestoChangeSummaryService(
            workspace
        ).build()
    )

    result = {
        row.key: row.difference
        for row in summary.by_budgeter
    }

    assert result == {
        "ANA": Decimal("10.00"),
        "LUIS": Decimal("10.00"),
    }


def test_disable_row_reduces_budget():
    workspace = build_workspace()

    workspace.set_enabled(
        0,
        False,
    )

    summary = (
        PresupuestoChangeSummaryService(
            workspace
        ).build()
    )

    assert (
        summary.original_total
        == Decimal("100.00")
    )

    assert (
        summary.simulated_total
        == Decimal("60.00")
    )

    assert (
        summary.difference
        == Decimal("-40.00")
    )