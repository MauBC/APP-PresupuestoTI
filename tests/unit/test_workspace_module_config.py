import pytest

from app.config.budget_module_config import (
    BudgetModule,
)
from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)


pytestmark = pytest.mark.unit


def test_workspace_defaults_to_opex():
    workspace = (
        PresupuestoWorkspace()
    )

    assert (
        workspace.module_config
        is OPEX_MODULE_CONFIG
    )

    assert (
        workspace.module_config.module
        == BudgetModule.OPEX
    )


def test_workspace_accepts_capex_config():
    workspace = (
        PresupuestoWorkspace(
            CAPEX_MODULE_CONFIG
        )
    )

    assert (
        workspace.module_config
        is CAPEX_MODULE_CONFIG
    )

    assert (
        workspace.module_config.module
        == BudgetModule.CAPEX
    )


def test_workspace_amount_columns_come_from_module():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    assert (
        workspace.amount_columns
        ==
        OPEX_MODULE_CONFIG
        .amount_columns
    )
