import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.config.new_budget_row_form import (
    get_new_budget_row_form,
)


pytestmark = pytest.mark.unit


def test_capex_form_covers_every_dimension_once():
    definition = (
        get_new_budget_row_form(
            CAPEX_MODULE_CONFIG
        )
    )

    assert (
        set(
            definition.columns
        )
        ==
        set(
            CAPEX_MODULE_CONFIG
            .dimension_columns
        )
    )

    assert (
        len(
            definition.columns
        )
        ==
        len(
            set(
                definition.columns
            )
        )
    )


def test_capex_form_has_business_sections():
    definition = (
        get_new_budget_row_form(
            CAPEX_MODULE_CONFIG
        )
    )

    titles = tuple(
        section.title
        for section
        in definition.sections
    )

    assert titles == (
        "Datos generales",
        "Aprobaci\u00f3n",
        "Clasificaci\u00f3n",
        "Imputaci\u00f3n",
        "Observaci\u00f3n",
    )


def test_capex_defaults_year_and_quantity():
    definition = (
        get_new_budget_row_form(
            CAPEX_MODULE_CONFIG
        )
    )

    assert (
        definition.default_map[
            "anio"
        ]
        == 2027
    )

    assert (
        definition.default_map[
            "cantidad"
        ]
        == 1
    )


def test_opex_uses_same_shared_form_contract():
    definition = (
        get_new_budget_row_form(
            OPEX_MODULE_CONFIG
        )
    )

    assert (
        set(
            definition.columns
        )
        ==
        set(
            OPEX_MODULE_CONFIG
            .dimension_columns
        )
    )

    assert (
        definition.default_map
        == {}
    )


def test_form_never_exposes_amount_columns_as_dimensions():
    for config in (
        OPEX_MODULE_CONFIG,
        CAPEX_MODULE_CONFIG,
    ):
        definition = (
            get_new_budget_row_form(
                config
            )
        )

        assert not (
            set(
                definition.columns
            )
            &
            set(
                config.amount_columns
            )
        )
