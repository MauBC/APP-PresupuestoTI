from decimal import Decimal

import pytest

from app.config.budget_module_config import (
    BudgetModule,
    BudgetModuleCapabilities,
    BudgetModuleConfig,
)
from app.services.dimension_allocation_service import (
    DimensionAllocationError,
    DimensionAllocationService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)


pytestmark = pytest.mark.unit


CONFIG = BudgetModuleConfig(
    module=BudgetModule.OPEX,
    label="OPEX TEST",
    main_table="test",
    dimension_columns=(
        "pais",
        "ceco",
        "presupuestador",
    ),
    groupable_columns=(
        "pais",
        "ceco",
        "presupuestador",
    ),
    month_columns=(
        "m1",
        "m2",
    ),
    annual_column="total",
    capabilities=(
        BudgetModuleCapabilities(
            monthly_distribution=True,
            ceco_distribution=True,
            country_distribution=True,
            grouped_editing=True,
        )
    ),
    country_column="pais",
    budgeter_column="presupuestador",
    ceco_column="ceco",
    configured=True,
)


NO_CECO_CONFIG = BudgetModuleConfig(
    module=BudgetModule.CAPEX,
    label="CAPEX TEST",
    main_table="capex_test",
    dimension_columns=(
        "ceco",
    ),
    groupable_columns=(
        "ceco",
    ),
    month_columns=(
        "m1",
        "m2",
    ),
    annual_column="total",
    capabilities=(
        BudgetModuleCapabilities(
            monthly_distribution=True,
            ceco_distribution=False,
            country_distribution=False,
            grouped_editing=True,
        )
    ),
    ceco_column="ceco",
    configured=True,
)


def make_row(
    *,
    pais="PERU",
    ceco,
    presupuestador="ANA",
    m1,
    m2,
    enabled=True,
):
    return {
        "pais": pais,
        "ceco": ceco,
        "presupuestador":
            presupuestador,
        "habilitado": enabled,
        "m1": Decimal(m1),
        "m2": Decimal(m2),
        "total": (
            Decimal(m1)
            + Decimal(m2)
        ),
    }


def build_workspace():
    workspace = (
        PresupuestoWorkspace(
            CONFIG
        )
    )

    workspace.load(
        (
            make_row(
                ceco="A",
                m1="30",
                m2="20",
            ),
            make_row(
                ceco="A",
                m1="10",
                m2="40",
            ),
            make_row(
                ceco="B",
                m1="20",
                m2="80",
            ),
        )
    )

    return workspace


def test_preview_calculates_dimension_targets():
    workspace = build_workspace()

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    preview = service.preview(
        dimension="ceco",
        percentages={
            "A": "25",
            "B": "75",
        },
    )

    result = {
        item.value:
            item.target_total
        for item
        in preview.items
    }

    assert (
        preview.current_total
        == Decimal("200.00")
    )

    assert result == {
        "A": Decimal("50.00"),
        "B": Decimal("150.00"),
    }


def test_apply_preserves_internal_proportions():
    workspace = build_workspace()

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    service.apply(
        dimension="ceco",
        percentages={
            "A": "25",
            "B": "75",
        },
    )

    row_0 = workspace.get_row(0)
    row_1 = workspace.get_row(1)
    row_2 = workspace.get_row(2)

    assert row_0["m1"] == Decimal("15.00")
    assert row_0["m2"] == Decimal("10.00")
    assert row_0["total"] == Decimal("25.00")

    assert row_1["m1"] == Decimal("5.00")
    assert row_1["m2"] == Decimal("20.00")
    assert row_1["total"] == Decimal("25.00")

    assert row_2["m1"] == Decimal("30.00")
    assert row_2["m2"] == Decimal("120.00")
    assert row_2["total"] == Decimal("150.00")

    assert (
        row_0["total"]
        + row_1["total"]
        + row_2["total"]
        == Decimal("200.00")
    )


def test_distribution_is_one_history_operation():
    workspace = build_workspace()

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    service.apply(
        dimension="ceco",
        percentages={
            "A": "25",
            "B": "75",
        },
    )

    assert workspace.history_count == 1
    assert workspace.pending_row_count == 3

    workspace.undo_last()

    assert workspace.history_count == 0
    assert workspace.pending_row_count == 0

    assert (
        workspace.get_row(0)["total"]
        == Decimal("50")
    )

    assert (
        workspace.get_row(2)["total"]
        == Decimal("100")
    )


def test_original_rows_are_preserved():
    workspace = build_workspace()

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    service.apply(
        dimension="ceco",
        percentages={
            "A": "25",
            "B": "75",
        },
    )

    assert (
        workspace
        .get_original_row(0)[
            "total"
        ]
        == Decimal("50")
    )


def test_percentage_below_100_is_rejected():
    workspace = build_workspace()

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    with pytest.raises(
        DimensionAllocationError,
        match="Falta",
    ):
        service.preview(
            dimension="ceco",
            percentages={
                "A": "25",
                "B": "74",
            },
        )


def test_percentage_above_100_is_rejected():
    workspace = build_workspace()

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    with pytest.raises(
        DimensionAllocationError,
        match="exceso",
    ):
        service.preview(
            dimension="ceco",
            percentages={
                "A": "25",
                "B": "76",
            },
        )


def test_missing_dimension_percentage_is_rejected():
    workspace = build_workspace()

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    with pytest.raises(
        DimensionAllocationError,
        match="Faltan porcentajes",
    ):
        service.preview(
            dimension="ceco",
            percentages={
                "A": "100",
            },
        )


def test_disabled_rows_are_excluded():
    workspace = (
        PresupuestoWorkspace(
            CONFIG
        )
    )

    workspace.load(
        (
            make_row(
                ceco="A",
                m1="50",
                m2="50",
            ),
            make_row(
                ceco="B",
                m1="50",
                m2="50",
                enabled=False,
            ),
        )
    )

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    preview = service.apply(
        dimension="ceco",
        percentages={
            "A": "100",
        },
    )

    assert preview.row_count == 1

    assert (
        workspace.get_row(1)[
            "total"
        ]
        == Decimal("100")
    )


def test_blank_dimension_is_rejected():
    workspace = (
        PresupuestoWorkspace(
            CONFIG
        )
    )

    workspace.load(
        (
            make_row(
                ceco="",
                m1="50",
                m2="50",
            ),
        )
    )

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    with pytest.raises(
        DimensionAllocationError,
        match="valores vacios",
    ):
        service.preview(
            dimension="ceco",
            percentages={
                "": "100",
            },
        )


def test_scope_limits_rows_before_distribution():
    workspace = (
        PresupuestoWorkspace(
            CONFIG
        )
    )

    workspace.load(
        (
            make_row(
                pais="PERU",
                ceco="A",
                m1="50",
                m2="50",
            ),
            make_row(
                pais="PERU",
                ceco="B",
                m1="50",
                m2="50",
            ),
            make_row(
                pais="CHILE",
                ceco="C",
                m1="100",
                m2="100",
            ),
        )
    )

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    preview = service.preview(
        dimension="ceco",
        scope_columns=(
            "pais",
        ),
        scope_values=(
            "PERU",
        ),
        percentages={
            "A": "40",
            "B": "60",
        },
    )

    assert (
        preview.current_total
        == Decimal("200.00")
    )

    assert preview.row_count == 2


def test_country_distribution_uses_same_engine():
    workspace = (
        PresupuestoWorkspace(
            CONFIG
        )
    )

    workspace.load(
        (
            make_row(
                pais="PERU",
                ceco="A",
                m1="50",
                m2="50",
            ),
            make_row(
                pais="CHILE",
                ceco="B",
                m1="50",
                m2="50",
            ),
        )
    )

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    preview = service.preview(
        dimension="pais",
        percentages={
            "PERU": "70",
            "CHILE": "30",
        },
    )

    targets = {
        item.value:
            item.target_total
        for item in preview.items
    }

    assert targets == {
        "PERU": Decimal("140.00"),
        "CHILE": Decimal("60.00"),
    }


def test_disabled_capability_is_rejected():
    workspace = (
        PresupuestoWorkspace(
            NO_CECO_CONFIG
        )
    )

    workspace.load(
        (
            {
                "ceco": "A",
                "habilitado": True,
                "m1": Decimal("50"),
                "m2": Decimal("50"),
                "total": Decimal("100"),
            },
        )
    )

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    with pytest.raises(
        DimensionAllocationError,
        match="no permite",
    ):
        service.preview(
            dimension="ceco",
            percentages={
                "A": "100",
            },
        )


def test_cent_residual_remains_exact():
    workspace = (
        PresupuestoWorkspace(
            CONFIG
        )
    )

    workspace.load(
        (
            make_row(
                ceco="A",
                m1="1",
                m2="0",
            ),
            make_row(
                ceco="B",
                m1="1",
                m2="0",
            ),
            make_row(
                ceco="C",
                m1="8",
                m2="0",
            ),
        )
    )

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    service.apply(
        dimension="ceco",
        percentages={
            "A": "33.33",
            "B": "33.33",
            "C": "33.34",
        },
    )

    total = sum(
        (
            workspace
            .get_row(index)[
                "total"
            ]
            for index
            in range(3)
        ),
        Decimal("0"),
    )

    assert total == Decimal("10.00")


def test_current_preview_preserves_current_totals():
    workspace = build_workspace()

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    preview = (
        service.current_preview(
            dimension="ceco"
        )
    )

    percentages = {
        item.value:
            item.percentage
        for item in preview.items
    }

    targets = {
        item.value:
            item.target_total
        for item in preview.items
    }

    assert percentages == {
        "A": Decimal("50.00"),
        "B": Decimal("50.00"),
    }

    assert targets == {
        "A": Decimal("100.00"),
        "B": Decimal("100.00"),
    }

    assert (
        preview.percentage_total
        == Decimal("100.00")
    )


def test_current_preview_respects_scope():
    workspace = (
        PresupuestoWorkspace(
            CONFIG
        )
    )

    workspace.load(
        (
            make_row(
                pais="PERU",
                ceco="A",
                m1="30",
                m2="70",
            ),
            make_row(
                pais="PERU",
                ceco="B",
                m1="50",
                m2="50",
            ),
            make_row(
                pais="CHILE",
                ceco="C",
                m1="100",
                m2="100",
            ),
        )
    )

    service = (
        DimensionAllocationService(
            workspace
        )
    )

    preview = (
        service.current_preview(
            dimension="ceco",
            scope_columns=(
                "pais",
            ),
            scope_values=(
                "PERU",
            ),
        )
    )

    assert (
        preview.current_total
        == Decimal("200.00")
    )

    assert {
        item.value
        for item in preview.items
    } == {
        "A",
        "B",
    }
