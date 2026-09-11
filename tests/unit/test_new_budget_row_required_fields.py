import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.config.new_budget_row_form import (
    get_missing_required_new_row_columns,
    get_new_budget_row_form,
)


pytestmark = pytest.mark.unit


def test_capex_required_columns_cover_summary_contract():
    definition = (
        get_new_budget_row_form(
            CAPEX_MODULE_CONFIG
        )
    )

    assert (
        definition.required_columns
        == (
            "nombre_inversion",
            "vicepresidencia",
            "pais",
            "responsable",
            "gerente_aprobador",
            "anio",
            "cantidad",
        )
    )


def test_opex_does_not_gain_capex_requirements():
    definition = (
        get_new_budget_row_form(
            OPEX_MODULE_CONFIG
        )
    )

    assert (
        definition.required_columns
        == ()
    )


def test_missing_required_detects_none_and_blank():
    definition = (
        get_new_budget_row_form(
            CAPEX_MODULE_CONFIG
        )
    )

    missing = (
        get_missing_required_new_row_columns(
            definition,
            {
                "nombre_inversion": "   ",
                "vicepresidencia": None,
                "pais": "Peru",
                "responsable": "Ana",
                "gerente_aprobador": "Luis",
                "anio": 2027,
                "cantidad": 1,
            },
        )
    )

    assert missing == (
        "nombre_inversion",
        "vicepresidencia",
    )


def test_complete_capex_required_values_pass():
    definition = (
        get_new_budget_row_form(
            CAPEX_MODULE_CONFIG
        )
    )

    missing = (
        get_missing_required_new_row_columns(
            definition,
            {
                "nombre_inversion":
                    "Proyecto CAPEX",
                "vicepresidencia":
                    "VP TI",
                "pais":
                    "Peru",
                "responsable":
                    "Ana",
                "gerente_aprobador":
                    "Luis",
                "anio":
                    2027,
                "cantidad":
                    1,
            },
        )
    )

    assert missing == ()


def test_zero_quantity_is_not_treated_as_missing():
    definition = (
        get_new_budget_row_form(
            CAPEX_MODULE_CONFIG
        )
    )

    missing = (
        get_missing_required_new_row_columns(
            definition,
            {
                "nombre_inversion":
                    "Proyecto CAPEX",
                "vicepresidencia":
                    "VP TI",
                "pais":
                    "Peru",
                "responsable":
                    "Ana",
                "gerente_aprobador":
                    "Luis",
                "anio":
                    2027,
                "cantidad":
                    0,
            },
        )
    )

    assert missing == ()
