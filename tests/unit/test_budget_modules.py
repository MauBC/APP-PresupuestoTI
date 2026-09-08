import pytest

from app.config.budget_module_config import (
    BudgetModule,
)
from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
    get_budget_module_config,
)


pytestmark = pytest.mark.unit


def test_opex_module_is_configured():
    config = (
        OPEX_MODULE_CONFIG
    )

    assert (
        config.module
        == BudgetModule.OPEX
    )

    assert config.configured

    assert (
        config.capabilities
        .monthly_distribution
    )

    assert (
        config.capabilities
        .ceco_distribution
    )

    assert (
        config.capabilities
        .country_distribution
    )


def test_capex_capabilities_are_restricted():
    config = (
        CAPEX_MODULE_CONFIG
    )

    assert (
        config.module
        == BudgetModule.CAPEX
    )

    assert not config.configured

    assert (
        config.capabilities
        .monthly_distribution
    )

    assert not (
        config.capabilities
        .ceco_distribution
    )

    assert not (
        config.capabilities
        .country_distribution
    )


def test_monthly_amount_model_is_shared():
    assert (
        OPEX_MODULE_CONFIG
        .amount_columns
        ==
        CAPEX_MODULE_CONFIG
        .amount_columns
    )

    assert (
        len(
            OPEX_MODULE_CONFIG
            .month_columns
        )
        == 12
    )


def test_module_lookup():
    assert (
        get_budget_module_config(
            "OPEX"
        )
        is OPEX_MODULE_CONFIG
    )

    assert (
        get_budget_module_config(
            BudgetModule.CAPEX
        )
        is CAPEX_MODULE_CONFIG
    )


def test_unknown_module_is_rejected():
    with pytest.raises(
        ValueError,
        match="no reconocido",
    ):
        get_budget_module_config(
            "OTRO"
        )
