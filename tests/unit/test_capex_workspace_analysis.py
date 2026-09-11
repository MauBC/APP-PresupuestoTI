from decimal import Decimal

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_analysis_service import (
    PresupuestoWorkspaceAnalysisService,
)


pytestmark = pytest.mark.unit


def make_row(
    *,
    row_id,
    pais,
    responsable,
    total,
):
    row = {
        column: None
        for column in (
            CAPEX_MODULE_CONFIG
            .dimension_columns
        )
    }

    row[
        "pais"
    ] = pais

    row[
        "responsable"
    ] = responsable

    row[
        "row_id"
    ] = row_id

    row[
        "version"
    ] = 1

    row[
        "habilitado"
    ] = True

    for column in (
        CAPEX_MODULE_CONFIG
        .amount_columns
    ):
        row[
            column
        ] = Decimal(
            "0"
        )

    row[
        CAPEX_MODULE_CONFIG
        .annual_column
    ] = Decimal(
        total
    )

    return row


def build_service():
    workspace = (
        PresupuestoWorkspace(
            CAPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        (
            make_row(
                row_id="row-1",
                pais="PER",
                responsable="Ana",
                total="100",
            ),
            make_row(
                row_id="row-2",
                pais="CHL",
                responsable="Luis",
                total="50",
            ),
        )
    )

    return (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )


def test_capex_dashboard_uses_responsable():
    service = build_service()

    result = (
        service.get_dashboard()
    )

    assert (
        result.total_usd
        == Decimal(
            "150"
        )
    )

    assert (
        result.total_rows
        == 2
    )

    assert (
        result.total_countries
        == 2
    )

    assert (
        result.total_budgeters
        == 2
    )

    values = {
        row[
            "presupuestador"
        ]
        for row in (
            result.by_budgeter
        )
    }

    assert values == {
        "Ana",
        "Luis",
    }


def test_capex_can_group_by_responsable():
    service = build_service()

    result = (
        service.get_grouped_totals(
            (
                "responsable",
            )
        )
    )

    assert (
        len(
            result.rows
        )
        == 2
    )

    assert (
        result.group_columns
        == (
            "responsable",
        )
    )

    totals = {
        row[
            "responsable"
        ]:
            row[
                CAPEX_MODULE_CONFIG
                .annual_column
            ]
        for row in result.rows
    }

    assert totals == {
        "Ana": Decimal(
            "100"
        ),
        "Luis": Decimal(
            "50"
        ),
    }

def test_capex_dashboard_exposes_advanced_metrics():
    first = make_row(
        row_id="row-1",
        pais="PER",
        responsable="Ana",
        total="100",
    )

    second = make_row(
        row_id="row-2",
        pais="CHL",
        responsable="Luis",
        total="50",
    )

    first[
        CAPEX_MODULE_CONFIG
        .month_columns[0]
    ] = Decimal("100")

    second[
        CAPEX_MODULE_CONFIG
        .month_columns[0]
    ] = Decimal("50")

    workspace = (
        PresupuestoWorkspace(
            CAPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        (
            first,
            second,
        )
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    result = service.get_dashboard()

    monthly = {
        item["column"]:
            item["total_usd"]
        for item
        in result.monthly_totals
    }

    assert (
        result.average_usd_per_row
        == Decimal("75.00")
    )

    assert (
        monthly[
            CAPEX_MODULE_CONFIG
            .month_columns[0]
        ]
        == Decimal("150")
    )

    assert (
        len(
            result.monthly_totals
        )
        == 12
    )



def test_capex_dashboard_can_filter_by_responsable():
    service = build_service()

    result = service.get_dashboard(
        budgeter_filter="Ana"
    )

    assert (
        result.total_usd
        == Decimal("100")
    )

    assert result.total_rows == 1
    assert result.total_countries == 1
    assert result.total_budgeters == 1


def test_capex_dashboard_filter_options_use_responsable():
    service = build_service()

    result = (
        service.get_dashboard_filter_options()
    )

    assert result["countries"] == (
        "CHL",
        "PER",
    )

    assert result["budgeters"] == (
        "Ana",
        "Luis",
    )
