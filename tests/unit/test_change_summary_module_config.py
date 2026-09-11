from decimal import Decimal

import pytest

from app.config.budget_module_config import (
    BudgetModule,
    BudgetModuleCapabilities,
    BudgetModuleConfig,
)
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


CAPEX_DETAIL_CONFIG = (
    BudgetModuleConfig(
        module=BudgetModule.CAPEX,
        label="CAPEX TEST",
        main_table="capex_test",
        dimension_columns=(
            "proyecto",
            "responsable",
        ),
        groupable_columns=(
            "proyecto",
            "responsable",
        ),
        month_columns=(
            OPEX_MODULE_CONFIG
            .month_columns
        ),
        annual_column=(
            OPEX_MODULE_CONFIG
            .annual_column
        ),
        capabilities=(
            BudgetModuleCapabilities(
                monthly_distribution=True,
                grouped_editing=True,
            )
        ),
        change_detail_columns=(
            "proyecto",
            "responsable",
        ),
        configured=True,
    )
)


def make_row(
    config,
    *,
    row_id,
    dimensions,
    enero,
):
    row = {
        **dimensions,
        "row_id": row_id,
        "version": 1,
        "habilitado": True,
    }

    for column in (
        config.month_columns
    ):
        row[column] = Decimal(
            "0.00"
        )

    row["enero_usd"] = Decimal(
        enero
    )

    row[
        config.annual_column
    ] = Decimal(
        enero
    )

    return row


def test_opex_detail_contains_business_context():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        (
            make_row(
                OPEX_MODULE_CONFIG,
                row_id="opex-1",
                dimensions={
                    "proveedor":
                        "PROVEEDOR A",
                    "nombre_gasto":
                        "LICENCIA",
                    "pais":
                        "PERU",
                    "ceco":
                        "CECO-100",
                    "presupuestador":
                        "ANA",
                },
                enero="100.00",
            ),
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
        detail
        for detail in summary.details
        if (
            detail.column
            == "enero_usd"
        )
    )

    assert detail.proveedor == (
        "PROVEEDOR A"
    )

    assert detail.nombre_gasto == (
        "LICENCIA"
    )

    assert detail.pais == "PERU"
    assert detail.ceco == "CECO-100"

    assert (
        detail.presupuestador
        == "ANA"
    )


def test_numeric_detail_contains_variation():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        (
            make_row(
                OPEX_MODULE_CONFIG,
                row_id="opex-1",
                dimensions={
                    "pais": "PERU",
                },
                enero="100.00",
            ),
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
        detail
        for detail in summary.details
        if (
            detail.column
            == "enero_usd"
        )
    )

    assert (
        detail.difference
        == Decimal("50.00")
    )

    assert (
        detail.variation_percent
        == Decimal("50.00")
    )


def test_capex_uses_its_own_detail_context():
    workspace = (
        PresupuestoWorkspace(
            CAPEX_DETAIL_CONFIG
        )
    )

    workspace.load(
        (
            make_row(
                CAPEX_DETAIL_CONFIG,
                row_id="capex-1",
                dimensions={
                    "proyecto":
                        "DATA CENTER",
                    "responsable":
                        "LUIS",
                },
                enero="500.00",
            ),
        )
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("600.00"),
    )

    summary = (
        PresupuestoChangeSummaryService(
            workspace
        ).build()
    )

    detail = next(
        detail
        for detail in summary.details
        if (
            detail.column
            == "enero_usd"
        )
    )

    assert detail.context_map == {
        "proyecto": "DATA CENTER",
        "responsable": "LUIS",
    }


def test_capex_does_not_invent_opex_breakdowns():
    workspace = (
        PresupuestoWorkspace(
            CAPEX_DETAIL_CONFIG
        )
    )

    workspace.load(
        (
            make_row(
                CAPEX_DETAIL_CONFIG,
                row_id="capex-1",
                dimensions={
                    "proyecto":
                        "DATA CENTER",
                    "responsable":
                        "LUIS",
                },
                enero="500.00",
            ),
        )
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("600.00"),
    )

    summary = (
        PresupuestoChangeSummaryService(
            workspace
        ).build()
    )

    assert summary.by_country == ()
    assert summary.by_budgeter == ()
