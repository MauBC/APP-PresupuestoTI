import pytest

from app.config.capex_schema import (
    CAPEX_AMOUNT_COLUMNS,
    CAPEX_DIMENSION_COLUMNS,
    CAPEX_USD_MONTH_COLUMNS,
    CAPEX_USD_TOTAL_COLUMN,
)
from app.config.budget_module_config import (
    BudgetModule,
)
from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
)
from app.config.settings import (
    settings,
)


pytestmark = pytest.mark.unit


def test_capex_has_24_dimensions():
    assert (
        len(
            CAPEX_DIMENSION_COLUMNS
        )
        == 24
    )


def test_capex_dimensions_exclude_amounts():
    assert not (
        set(
            CAPEX_DIMENSION_COLUMNS
        )
        & set(
            CAPEX_AMOUNT_COLUMNS
        )
    )


def test_capex_module_uses_real_schema():
    assert (
        CAPEX_MODULE_CONFIG.module
        == BudgetModule.CAPEX
    )

    assert (
        CAPEX_MODULE_CONFIG.main_table
        == settings.BIGQUERY_CAPEX_TABLE
    )

    assert (
        CAPEX_MODULE_CONFIG.dimension_columns
        == CAPEX_DIMENSION_COLUMNS
    )

    assert (
        CAPEX_MODULE_CONFIG.month_columns
        == CAPEX_USD_MONTH_COLUMNS
    )

    assert (
        CAPEX_MODULE_CONFIG.annual_column
        == CAPEX_USD_TOTAL_COLUMN
    )


def test_capex_gui_remains_disabled():
    assert (
        CAPEX_MODULE_CONFIG.configured
        is False
    )
