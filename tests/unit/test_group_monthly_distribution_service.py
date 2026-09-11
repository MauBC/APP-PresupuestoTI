from decimal import Decimal

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.services.group_monthly_distribution_service import (
    GroupMonthlyDistributionError,
    GroupMonthlyDistributionService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)


pytestmark = pytest.mark.unit


def percentages(
    enero="25.00",
    febrero="75.00",
):
    result = {
        month: Decimal("0.00")
        for month
        in OPEX_MODULE_CONFIG
        .month_columns
    }

    result[
        "enero_usd"
    ] = Decimal(
        enero
    )

    result[
        "febrero_usd"
    ] = Decimal(
        febrero
    )

    return result


def make_row(
    config,
    *,
    group_column,
    group_value,
    enero,
    febrero,
    enabled=True,
):
    row = {
        group_column:
            group_value,
        "habilitado":
            enabled,
    }

    for month in (
        config.month_columns
    ):
        row[month] = (
            Decimal("0.00")
        )

    row["enero_usd"] = Decimal(
        enero
    )

    row["febrero_usd"] = Decimal(
        febrero
    )

    row[
        config.annual_column
    ] = (
        Decimal(enero)
        + Decimal(febrero)
    )

    return row


def build_opex():
    workspace = PresupuestoWorkspace(
        OPEX_MODULE_CONFIG
    )

    workspace.load(
        (
            make_row(
                OPEX_MODULE_CONFIG,
                group_column="pais",
                group_value="PERU",
                enero="10.00",
                febrero="30.00",
            ),
            make_row(
                OPEX_MODULE_CONFIG,
                group_column="pais",
                group_value="PERU",
                enero="20.00",
                febrero="40.00",
            ),
        )
    )

    return (
        workspace,
        GroupMonthlyDistributionService(
            workspace
        ),
    )


def test_group_monthly_distribution_changes_pattern():
    workspace, service = (
        build_opex()
    )

    preview = service.apply(
        group_columns=("pais",),
        group_values=("PERU",),
        percentages=(
            percentages()
        ),
        annual_total="200.00",
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

    row_a = workspace.get_row(0)
    row_b = workspace.get_row(1)

    assert (
        row_a["anio_usd"]
        == Decimal("80.00")
    )
    assert (
        row_b["anio_usd"]
        == Decimal("120.00")
    )

    assert (
        row_a["enero_usd"]
        == Decimal("20.00")
    )
    assert (
        row_a["febrero_usd"]
        == Decimal("60.00")
    )

    assert (
        row_b["enero_usd"]
        == Decimal("30.00")
    )
    assert (
        row_b["febrero_usd"]
        == Decimal("90.00")
    )

    assert (
        row_a["enero_usd"]
        + row_b["enero_usd"]
        == Decimal("50.00")
    )

    assert (
        row_a["febrero_usd"]
        + row_b["febrero_usd"]
        == Decimal("150.00")
    )


def test_group_distribution_is_one_undo_operation():
    workspace, service = (
        build_opex()
    )

    service.apply(
        group_columns=("pais",),
        group_values=("PERU",),
        percentages=(
            percentages(
                enero="50.00",
                febrero="50.00",
            )
        ),
        annual_total="100.00",
    )

    assert (
        workspace.history_count
        == 1
    )

    workspace.undo_last()

    assert (
        workspace.get_row(0)[
            "enero_usd"
        ]
        == Decimal("10.00")
    )

    assert (
        workspace.get_row(0)[
            "febrero_usd"
        ]
        == Decimal("30.00")
    )

    assert (
        workspace.get_row(1)[
            "enero_usd"
        ]
        == Decimal("20.00")
    )

    assert (
        workspace.get_row(1)[
            "febrero_usd"
        ]
        == Decimal("40.00")
    )


def test_disabled_rows_are_not_modified():
    workspace = PresupuestoWorkspace(
        OPEX_MODULE_CONFIG
    )

    workspace.load(
        (
            make_row(
                OPEX_MODULE_CONFIG,
                group_column="pais",
                group_value="PERU",
                enero="50.00",
                febrero="50.00",
                enabled=True,
            ),
            make_row(
                OPEX_MODULE_CONFIG,
                group_column="pais",
                group_value="PERU",
                enero="100.00",
                febrero="100.00",
                enabled=False,
            ),
        )
    )

    service = (
        GroupMonthlyDistributionService(
            workspace
        )
    )

    preview = service.apply(
        group_columns=("pais",),
        group_values=("PERU",),
        percentages=(
            percentages(
                enero="25.00",
                febrero="75.00",
            )
        ),
        annual_total="200.00",
    )

    assert preview.row_count == 1

    assert (
        workspace.get_row(0)[
            "enero_usd"
        ]
        == Decimal("50.00")
    )

    assert (
        workspace.get_row(0)[
            "febrero_usd"
        ]
        == Decimal("150.00")
    )

    assert (
        workspace.get_row(1)[
            "enero_usd"
        ]
        == Decimal("100.00")
    )

    assert (
        workspace.get_row(1)[
            "febrero_usd"
        ]
        == Decimal("100.00")
    )


def test_zero_group_rejects_positive_target():
    workspace = PresupuestoWorkspace(
        OPEX_MODULE_CONFIG
    )

    workspace.load(
        (
            make_row(
                OPEX_MODULE_CONFIG,
                group_column="pais",
                group_value="PERU",
                enero="0.00",
                febrero="0.00",
            ),
        )
    )

    service = (
        GroupMonthlyDistributionService(
            workspace
        )
    )

    with pytest.raises(
        GroupMonthlyDistributionError,
        match="distribucion anual previa",
    ):
        service.apply(
            group_columns=("pais",),
            group_values=("PERU",),
            percentages=(
                percentages()
            ),
            annual_total="100.00",
        )


def test_capex_uses_same_group_distribution_engine():
    workspace = PresupuestoWorkspace(
        CAPEX_MODULE_CONFIG
    )

    workspace.load(
        (
            make_row(
                CAPEX_MODULE_CONFIG,
                group_column="responsable",
                group_value="ANA",
                enero="40.00",
                febrero="60.00",
            ),
            make_row(
                CAPEX_MODULE_CONFIG,
                group_column="responsable",
                group_value="ANA",
                enero="100.00",
                febrero="100.00",
            ),
        )
    )

    service = (
        GroupMonthlyDistributionService(
            workspace
        )
    )

    preview = service.apply(
        group_columns=(
            "responsable",
        ),
        group_values=(
            "ANA",
        ),
        percentages=(
            percentages(
                enero="50.00",
                febrero="50.00",
            )
        ),
        annual_total="600.00",
    )

    assert preview.row_count == 2

    assert (
        sum(
            (
                workspace
                .get_row(index)[
                    "anio_usd"
                ]
                for index
                in range(2)
            ),
            Decimal("0.00"),
        )
        == Decimal("600.00")
    )

    assert (
        sum(
            (
                workspace
                .get_row(index)[
                    "enero_usd"
                ]
                for index
                in range(2)
            ),
            Decimal("0.00"),
        )
        == Decimal("300.00")
    )

    assert (
        sum(
            (
                workspace
                .get_row(index)[
                    "febrero_usd"
                ]
                for index
                in range(2)
            ),
            Decimal("0.00"),
        )
        == Decimal("300.00")
    )
