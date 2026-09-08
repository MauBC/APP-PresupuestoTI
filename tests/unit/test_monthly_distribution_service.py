from decimal import Decimal

import pytest

from app.config.budget_module_config import (
    BudgetModule,
    BudgetModuleCapabilities,
    BudgetModuleConfig,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.usd_allocation_service import (
    UsdAllocationError,
    UsdAllocationService,
)


pytestmark = pytest.mark.unit


CUSTOM_CONFIG = (
    BudgetModuleConfig(
        module=BudgetModule.CAPEX,
        label="CAPEX TEST",
        main_table="capex_test",
        dimension_columns=(
            "proyecto",
        ),
        groupable_columns=(
            "proyecto",
        ),
        month_columns=(
            "mes_1",
            "mes_2",
            "mes_3",
        ),
        annual_column="total_anual",
        capabilities=(
            BudgetModuleCapabilities(
                monthly_distribution=True,
                grouped_editing=True,
            )
        ),
        change_detail_columns=(
            "proyecto",
        ),
        configured=True,
    )
)


def make_custom_row():
    return {
        "proyecto": "PROYECTO A",
        "row_id": "row-1",
        "version": 1,
        "habilitado": True,
        "mes_1": Decimal("2.00"),
        "mes_2": Decimal("3.00"),
        "mes_3": Decimal("5.00"),
        "total_anual": Decimal("10.00"),
    }


def test_set_month_uses_custom_module_columns():
    row = make_custom_row()

    result = (
        UsdAllocationService.set_month(
            row,
            "mes_1",
            Decimal("4.00"),
            month_columns=(
                CUSTOM_CONFIG
                .month_columns
            ),
            annual_column=(
                CUSTOM_CONFIG
                .annual_column
            ),
        )
    )

    assert (
        result["mes_1"]
        == Decimal("4.00")
    )

    assert (
        result["total_anual"]
        == Decimal("12.00")
    )


def test_percentage_distribution_is_exact():
    row = make_custom_row()

    result = (
        UsdAllocationService
        .set_percentage_distribution(
            row,
            {
                "mes_1":
                    Decimal("33.33"),
                "mes_2":
                    Decimal("33.33"),
                "mes_3":
                    Decimal("33.34"),
            },
            total=Decimal("10.00"),
            month_columns=(
                CUSTOM_CONFIG
                .month_columns
            ),
            annual_column=(
                CUSTOM_CONFIG
                .annual_column
            ),
        )
    )

    assert (
        result["mes_1"]
        + result["mes_2"]
        + result["mes_3"]
        == Decimal("10.00")
    )

    assert (
        result["total_anual"]
        == Decimal("10.00")
    )


def test_distribution_below_100_is_rejected():
    row = make_custom_row()

    with pytest.raises(
        UsdAllocationError,
        match="Falta",
    ):
        (
            UsdAllocationService
            .set_percentage_distribution(
                row,
                {
                    "mes_1": "40",
                    "mes_2": "40",
                    "mes_3": "19",
                },
                month_columns=(
                    CUSTOM_CONFIG
                    .month_columns
                ),
                annual_column=(
                    CUSTOM_CONFIG
                    .annual_column
                ),
            )
        )


def test_distribution_above_100_is_rejected():
    row = make_custom_row()

    with pytest.raises(
        UsdAllocationError,
        match="exceso",
    ):
        (
            UsdAllocationService
            .set_percentage_distribution(
                row,
                {
                    "mes_1": "40",
                    "mes_2": "40",
                    "mes_3": "21",
                },
                month_columns=(
                    CUSTOM_CONFIG
                    .month_columns
                ),
                annual_column=(
                    CUSTOM_CONFIG
                    .annual_column
                ),
            )
        )


def test_null_month_remains_unavailable():
    row = make_custom_row()

    row["mes_2"] = None

    with pytest.raises(
        UsdAllocationError,
        match="no esta disponible",
    ):
        (
            UsdAllocationService
            .set_percentage_distribution(
                row,
                {
                    "mes_1": "50",
                    "mes_2": "10",
                    "mes_3": "40",
                },
                month_columns=(
                    CUSTOM_CONFIG
                    .month_columns
                ),
                annual_column=(
                    CUSTOM_CONFIG
                    .annual_column
                ),
            )
        )


def test_negative_percentage_is_rejected():
    row = make_custom_row()

    with pytest.raises(
        UsdAllocationError,
        match="no pueden ser negativos",
    ):
        (
            UsdAllocationService
            .set_percentage_distribution(
                row,
                {
                    "mes_1": "-10",
                    "mes_2": "50",
                    "mes_3": "60",
                },
                month_columns=(
                    CUSTOM_CONFIG
                    .month_columns
                ),
                annual_column=(
                    CUSTOM_CONFIG
                    .annual_column
                ),
            )
        )


def test_workspace_distribution_is_one_operation():
    workspace = (
        PresupuestoWorkspace(
            CUSTOM_CONFIG
        )
    )

    workspace.load(
        (
            make_custom_row(),
        )
    )

    changed = (
        workspace
        .edit_monthly_distribution(
            0,
            {
                "mes_1": "20",
                "mes_2": "30",
                "mes_3": "50",
            },
            annual_total=(
                Decimal("20.00")
            ),
        )
    )

    row = workspace.get_row(
        0
    )

    assert changed is True

    assert (
        row["mes_1"]
        == Decimal("4.00")
    )

    assert (
        row["mes_2"]
        == Decimal("6.00")
    )

    assert (
        row["mes_3"]
        == Decimal("10.00")
    )

    assert (
        row["total_anual"]
        == Decimal("20.00")
    )

    assert (
        workspace.history_count
        == 1
    )

    assert (
        workspace.pending_row_count
        == 1
    )
