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
from app.services.presupuesto_group_edit_service import (
    PresupuestoGroupEditService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_analysis_service import (
    PresupuestoWorkspaceAnalysisService,
)
from database.persistence.bigquery_repository import (
    BigQueryPersistenceRepository,
)


pytestmark = pytest.mark.unit


TEST_CAPEX_CONFIG = (
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
                ceco_distribution=False,
                country_distribution=False,
                grouped_editing=True,
            )
        ),
        configured=True,
    )
)


def make_capex_row(
    proyecto,
    enero,
):
    row = {
        "proyecto": proyecto,
        "habilitado": True,
        "row_id": (
            f"row-{proyecto}"
        ),
        "version": 1,
    }

    for column in (
        TEST_CAPEX_CONFIG
        .month_columns
    ):
        row[column] = Decimal(
            "0.00"
        )

    row["enero_usd"] = Decimal(
        enero
    )

    row[
        TEST_CAPEX_CONFIG
        .annual_column
    ] = Decimal(
        enero
    )

    return row


def test_analysis_uses_module_columns():
    workspace = (
        PresupuestoWorkspace(
            TEST_CAPEX_CONFIG
        )
    )

    workspace.load(
        (
            make_capex_row(
                "PROYECTO A",
                "100.00",
            ),
        )
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    result = service.get_page(
        page_index=0,
        page_size=100,
    )

    assert (
        result.columns
        ==
        (
            "proyecto",
            "habilitado",
            *TEST_CAPEX_CONFIG
            .amount_columns,
        )
    )


def test_analysis_groups_using_module_config():
    workspace = (
        PresupuestoWorkspace(
            TEST_CAPEX_CONFIG
        )
    )

    workspace.load(
        (
            make_capex_row(
                "PROYECTO A",
                "100.00",
            ),
            make_capex_row(
                "PROYECTO B",
                "50.00",
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
            ("proyecto",)
        )
    )

    assert len(result.rows) == 2

    with pytest.raises(
        ValueError
    ):
        service.get_grouped_totals(
            ("pais",)
        )


def test_group_edit_uses_module_dimensions():
    workspace = (
        PresupuestoWorkspace(
            TEST_CAPEX_CONFIG
        )
    )

    workspace.load(
        (
            make_capex_row(
                "PROYECTO A",
                "100.00",
            ),
        )
    )

    service = (
        PresupuestoGroupEditService(
            workspace
        )
    )

    service.apply(
        group_columns=(
            "proyecto",
        ),
        group_values=(
            "PROYECTO A",
        ),
        column="enero_usd",
        target_total="150.00",
    )

    assert (
        workspace.get_row(
            0
        )["enero_usd"]
        == Decimal("150.00")
    )

    assert (
        workspace.get_row(
            0
        )["anio_usd"]
        == Decimal("150.00")
    )


def test_persistence_target_uses_module_table():
    repository = (
        BigQueryPersistenceRepository(
            object(),
            project="project-test",
            dataset="dataset-test",
            location="US",
            module_config=(
                TEST_CAPEX_CONFIG
            ),
        )
    )

    assert (
        repository.main_table_id
        ==
        "project-test."
        "dataset-test."
        "capex_test"
    )

    assert (
        repository.batch_table_id
        ==
        "project-test."
        "dataset-test."
        "presupuesto_change_batches"
    )
