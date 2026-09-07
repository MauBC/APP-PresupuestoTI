from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_workspace import (
    SESSION_ROW_ID,
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_analysis_service import (
    PresupuestoWorkspaceAnalysisService,
)


pytestmark = pytest.mark.unit


def make_row(
    *,
    pais,
    presupuestador,
    gasto,
    enero,
    febrero,
):
    row = {
        "pais": pais,
        "presupuestador": presupuestador,
        "nombre_gasto": gasto,
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal("0.00")

    row["enero_usd"] = Decimal(enero)
    row["febrero_usd"] = Decimal(febrero)

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
                enero="10",
                febrero="30",
            ),
            make_row(
                pais="PERU",
                presupuestador="ANA",
                gasto="B",
                enero="20",
                febrero="20",
            ),
            make_row(
                pais="CHILE",
                presupuestador="LUIS",
                gasto="C",
                enero="50",
                febrero="10",
            ),
        ]
    )

    return workspace


def test_page_uses_workspace_rows():
    workspace = build_workspace()

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    result = service.get_page(
        page_index=0,
        page_size=2,
    )

    assert result.total_rows == 3
    assert len(result.rows) == 2

    assert (
        result.rows[0][SESSION_ROW_ID]
        == 0
    )

    assert (
        result.rows[1][SESSION_ROW_ID]
        == 1
    )


def test_grouping_counts_source_rows():
    workspace = build_workspace()

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    result = service.get_grouped_totals(
        ("pais",)
    )

    peru = next(
        row
        for row in result.rows
        if row["pais"] == "PERU"
    )

    assert peru["registros"] == 2

    assert (
        peru["anio_usd"]
        == Decimal("80")
    )


def test_dashboard_uses_working_values():
    workspace = build_workspace()

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    before = service.get_dashboard()

    assert (
        before.total_usd
        == Decimal("140")
    )

    workspace.edit_annual(
        0,
        Decimal("80"),
    )

    after = service.get_dashboard()

    assert (
        after.total_usd
        == Decimal("180.00")
    )


def test_grouping_reflects_simulation():
    workspace = build_workspace()

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("30"),
    )

    result = service.get_grouped_totals(
        ("pais",)
    )

    peru = next(
        row
        for row in result.rows
        if row["pais"] == "PERU"
    )

    assert (
        peru["enero_usd"]
        == Decimal("50.00")
    )

    assert (
        peru["anio_usd"]
        == Decimal("100.00")
    )


def test_grouping_two_dimensions():
    workspace = build_workspace()

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    result = service.get_grouped_totals(
        (
            "pais",
            "presupuestador",
        )
    )

    assert len(result.rows) == 2

    peru_ana = next(
        row
        for row in result.rows
        if (
            row["pais"] == "PERU"
            and
            row["presupuestador"] == "ANA"
        )
    )

    assert peru_ana["registros"] == 2


def test_invalid_group_is_rejected():
    workspace = build_workspace()

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    with pytest.raises(ValueError):
        service.get_grouped_totals(
            ("vp",)
        )