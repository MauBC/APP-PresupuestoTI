from decimal import Decimal

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.config.grouping_config import (
    MAX_GROUPING_LEVELS,
)
from app.services.dimension_allocation_service import (
    DimensionAllocationService,
)
from app.services.group_monthly_distribution_service import (
    GroupMonthlyDistributionService,
)
from app.services.presupuesto_analysis_service import (
    PresupuestoAnalysisService,
)
from app.services.presupuesto_group_edit_service import (
    PresupuestoGroupEditService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_analysis_service import (
    PresupuestoWorkspaceAnalysisService,
)


pytestmark = pytest.mark.unit


MODULES = (
    OPEX_MODULE_CONFIG,
    CAPEX_MODULE_CONFIG,
)


def make_row(
    config,
    dimensions,
):
    row = {
        column: None
        for column
        in config.dimension_columns
    }

    row.update(
        dimensions
    )

    for month in (
        config.month_columns
    ):
        row[month] = Decimal(
            "0.00"
        )

    row[
        config.month_columns[0]
    ] = Decimal(
        "100.00"
    )

    row[
        config.annual_column
    ] = Decimal(
        "100.00"
    )

    row["habilitado"] = True

    return row


@pytest.mark.parametrize(
    "config",
    MODULES,
)
def test_workspace_analysis_accepts_five_groups(
    config,
):
    columns = tuple(
        config.groupable_columns[
            :MAX_GROUPING_LEVELS
        ]
    )

    assert len(columns) == 5

    dimensions = {
        column:
            f"value-{index}"
        for index, column
        in enumerate(
            columns
        )
    }

    workspace = PresupuestoWorkspace(
        config
    )

    workspace.load(
        (
            make_row(
                config,
                dimensions,
            ),
        )
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    result = (
        service.get_grouped_totals(
            columns
        )
    )

    assert (
        result.group_columns
        == columns
    )

    assert len(result.rows) == 1


@pytest.mark.parametrize(
    "config",
    MODULES,
)
def test_workspace_analysis_rejects_six_groups(
    config,
):
    columns = tuple(
        config.groupable_columns[:6]
    )

    assert len(columns) == 6

    workspace = PresupuestoWorkspace(
        config
    )

    workspace.load(
        ()
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    with pytest.raises(
        ValueError,
        match="5",
    ):
        service.get_grouped_totals(
            columns
        )


@pytest.mark.parametrize(
    "config",
    MODULES,
)
def test_group_edit_accepts_five_dimensions(
    config,
):
    columns = tuple(
        config.groupable_columns[:5]
    )

    values = tuple(
        f"value-{index}"
        for index
        in range(5)
    )

    dimensions = dict(
        zip(
            columns,
            values,
        )
    )

    workspace = PresupuestoWorkspace(
        config
    )

    workspace.load(
        (
            make_row(
                config,
                dimensions,
            ),
        )
    )

    service = (
        PresupuestoGroupEditService(
            workspace
        )
    )

    preview = service.preview(
        group_columns=columns,
        group_values=values,
        column=config.annual_column,
        target_total="100.00",
    )

    assert preview.row_count == 1
    assert (
        preview.group_columns
        == columns
    )


@pytest.mark.parametrize(
    "config",
    MODULES,
)
def test_group_monthly_distribution_accepts_five_dimensions(
    config,
):
    columns = tuple(
        config.groupable_columns[:5]
    )

    values = tuple(
        f"value-{index}"
        for index
        in range(5)
    )

    dimensions = dict(
        zip(
            columns,
            values,
        )
    )

    workspace = PresupuestoWorkspace(
        config
    )

    workspace.load(
        (
            make_row(
                config,
                dimensions,
            ),
        )
    )

    percentages = {
        month: Decimal("0.00")
        for month
        in config.month_columns
    }

    percentages[
        config.month_columns[0]
    ] = Decimal("100.00")

    service = (
        GroupMonthlyDistributionService(
            workspace
        )
    )

    preview = service.preview(
        group_columns=columns,
        group_values=values,
        percentages=percentages,
        annual_total="100.00",
    )

    assert preview.row_count == 1
    assert (
        preview.group_columns
        == columns
    )


def test_dimension_distribution_accepts_five_scope_columns():
    config = OPEX_MODULE_CONFIG

    dimension = (
        config.ceco_column
    )

    scope_columns = tuple(
        column
        for column
        in config.groupable_columns
        if column != dimension
    )[:5]

    assert len(scope_columns) == 5

    scope_values = tuple(
        f"scope-{index}"
        for index
        in range(5)
    )

    dimensions = dict(
        zip(
            scope_columns,
            scope_values,
        )
    )

    dimensions[
        dimension
    ] = "CECO-1"

    workspace = PresupuestoWorkspace(
        config
    )

    workspace.load(
        (
            make_row(
                config,
                dimensions,
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
            dimension=dimension,
            scope_columns=(
                scope_columns
            ),
            scope_values=(
                scope_values
            ),
        )
    )

    assert (
        preview.scope_columns
        == scope_columns
    )

    assert preview.row_count == 1


def test_all_grouping_services_share_same_limit():
    assert MAX_GROUPING_LEVELS == 5

    assert (
        PresupuestoWorkspaceAnalysisService
        .MAX_GROUP_COLUMNS
        == 5
    )

    assert (
        PresupuestoGroupEditService
        .MAX_GROUP_COLUMNS
        == 5
    )

    assert (
        GroupMonthlyDistributionService
        .MAX_GROUP_COLUMNS
        == 5
    )

    assert (
        DimensionAllocationService
        .MAX_SCOPE_COLUMNS
        == 5
    )

    assert (
        PresupuestoAnalysisService
        .MAX_GROUP_COLUMNS
        == 5
    )
