import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)


pytestmark = pytest.mark.unit


def test_opex_declares_country_dimension():
    assert (
        OPEX_MODULE_CONFIG
        .country_column
        == "pais"
    )


def test_opex_declares_budgeter_dimension():
    assert (
        OPEX_MODULE_CONFIG
        .budgeter_column
        == "presupuestador"
    )


def test_capex_does_not_inherit_opex_dimensions():
    assert (
        CAPEX_MODULE_CONFIG
        .country_column
        is None
    )

    assert (
        CAPEX_MODULE_CONFIG
        .budgeter_column
        is None
    )
