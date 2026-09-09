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
