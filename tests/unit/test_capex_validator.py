from decimal import Decimal

import pytest

from app.services.capex_validator import (
    clean_and_validate_capex_row,
)


pytestmark = pytest.mark.unit


def make_row():
    return {
        "Tipo": "PB",
        "Vicepresidencia": "Andina",
        "Pa\u00eds": "Per\u00fa",
        "Sociedad": "Ransa Comercial",
        "A\u00f1o": 2027,
        "Responsable": "Mauro",
        "Gerente Aprobador": "Gerente",
        "VP Aprobador": "VP",
        "Tipo de Activo": "Software",
        "Tipo de CAPEX": "Mantenimiento",
        "Clasificaci\u00f3n Inversi\u00f3n":
            "Mantenimiento",
        "Filtro TI": "TI",
        "Nombre de Inversi\u00f3n":
            "Proyecto CAPEX",
        "Cantidad": 1,
        "Breve Descripci\u00f3n de la Inversi\u00f3n":
            "Proyecto de prueba",
        "Codigo CEBE": "04WF2EAF90",
        "GYP": "COSTOS FIJOS",
        "Codigo CECO": "04WF2EAF93",
        "Desc_CeBe": "SEDE",
        "Sede CG": "LIMA",
        "U.Productiva CG": "LIMA",
        "Seg Rs": "SISTEMAS",
        "Moneda de facturaci\u00f3n": "PEN",

        "01 ML": 100,
        "02 ML": 200,
        "TOTAL ML": 300,

        "01 USD": 30,
        "02 USD": 70,
        "TOTAL USD": 100,

        "Observaci\u00f3n/Comentario":
            None,
    }


def test_valid_row_is_cleaned():
    result = (
        clean_and_validate_capex_row(
            make_row(),
            row_number=9,
        )
    )

    assert result.is_valid

    assert (
        result.row[
            "codigo_cebe"
        ]
        == "04WF2EAF90"
    )

    assert (
        result.row[
            "codigo_ceco"
        ]
        == "04WF2EAF93"
    )

    assert (
        result.row[
            "enero_ml"
        ]
        == Decimal("100.00")
    )

    assert (
        result.row[
            "febrero_ml"
        ]
        == Decimal("200.00")
    )

    assert (
        result.row[
            "anio_ml"
        ]
        == Decimal("300.00")
    )


def test_missing_month_is_zero():
    row = make_row()

    row["02 ML"] = None
    row["TOTAL ML"] = 100

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert result.is_valid

    assert (
        result.row[
            "febrero_ml"
        ]
        == Decimal("0.00")
    )

    assert (
        result.row[
            "anio_ml"
        ]
        == Decimal("100.00")
    )


def test_total_mismatch_is_error():
    row = make_row()

    row["TOTAL ML"] = 999

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert not result.is_valid

    assert (
        result.row[
            "anio_ml"
        ]
        == Decimal("300.00")
    )

    assert any(
        issue.code
        == "TOTAL_MISMATCH"
        and issue.column
        == "anio_ml"
        for issue
        in result.errors
    )


def test_blank_total_is_calculated():
    row = make_row()

    row["TOTAL USD"] = None

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert result.is_valid

    assert (
        result.row[
            "anio_usd"
        ]
        == Decimal("100.00")
    )

    assert any(
        issue.code
        == "TOTAL_CALCULATED"
        for issue
        in result.warnings
    )


def test_wrong_year_is_error():
    row = make_row()

    row["A\u00f1o"] = 2026

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert not result.is_valid

    assert any(
        issue.code
        == "YEAR_MISMATCH"
        for issue
        in result.errors
    )


def test_sample_year_can_be_accepted_for_analysis():
    row = make_row()

    row["A\u00f1o"] = 2026

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
            expected_year=None,
        )
    )

    assert result.is_valid


def test_cebe_and_ceco_can_be_null():
    row = make_row()

    row["Codigo CEBE"] = ""
    row["Codigo CECO"] = "-"

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert result.is_valid

    assert (
        result.row[
            "codigo_cebe"
        ]
        is None
    )

    assert (
        result.row[
            "codigo_ceco"
        ]
        is None
    )


def test_excel_error_blocks_row():
    row = make_row()

    row["03 USD"] = "#N/A"

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert not result.is_valid

    assert any(
        issue.code
        == "INVALID_AMOUNT"
        and issue.column
        == "marzo_usd"
        for issue
        in result.errors
    )


def test_quantity_must_be_integer():
    row = make_row()

    row["Cantidad"] = "1.5"

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert not result.is_valid

    assert any(
        issue.code
        == "INVALID_INTEGER"
        and issue.column
        == "cantidad"
        for issue
        in result.errors
    )

def test_small_total_rounding_difference_is_warning():
    row = make_row()

    row["TOTAL USD"] = (
        "100.005"
    )

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert result.is_valid

    assert (
        result.row[
            "anio_usd"
        ]
        == Decimal(
            "100.000000000"
        )
    )

    assert any(
        issue.code
        == "TOTAL_ROUNDING_DIFFERENCE"
        for issue
        in result.warnings
    )


def test_large_total_difference_is_error():
    row = make_row()

    row["TOTAL USD"] = (
        "100.02"
    )

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert not result.is_valid

    assert any(
        issue.code
        == "TOTAL_MISMATCH"
        and issue.column
        == "anio_usd"
        for issue
        in result.errors
    )

def test_nullable_excel_error_becomes_null():
    row = make_row()

    row["Codigo CECO"] = (
        "#N/A"
    )

    row["Desc_CeBe"] = (
        "#N/A"
    )

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert result.is_valid

    assert (
        result.row[
            "codigo_ceco"
        ]
        is None
    )

    assert (
        result.row[
            "desc_cebe"
        ]
        is None
    )

    assert sum(
        issue.code
        == "NULLABLE_TEXT_NORMALIZED"
        for issue
        in result.information
    ) == 2


def test_excel_error_in_required_text_is_error():
    row = make_row()

    row["Sociedad"] = (
        "#N/A"
    )

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert not result.is_valid

    assert any(
        issue.code
        == "INVALID_TEXT"
        and issue.column
        == "sociedad"
        for issue
        in result.errors
    )


def test_numeric_noise_does_not_create_warning():
    row = make_row()

    row["01 USD"] = (
        "33.333333333"
    )

    row["02 USD"] = (
        "66.666666668"
    )

    row["TOTAL USD"] = (
        "100.000000000"
    )

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert result.is_valid

    assert not any(
        issue.code
        == "TOTAL_ROUNDING_DIFFERENCE"
        for issue
        in result.warnings
    )

@pytest.mark.parametrize(
    "value",
    (
        None,
        "",
        "   ",
        "-",
    ),
)
def test_blank_quantity_defaults_to_one(
    value,
):
    row = make_row()

    row["Cantidad"] = value

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert result.is_valid

    assert (
        result.row["cantidad"]
        == 1
    )

    assert any(
        issue.code
        == "QUANTITY_DEFAULTED"
        and issue.column
        == "cantidad"
        for issue
        in result.information
    )


def test_explicit_quantity_is_preserved():
    row = make_row()

    row["Cantidad"] = 7

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    assert result.is_valid

    assert (
        result.row["cantidad"]
        == 7
    )

    assert not any(
        issue.code
        == "QUANTITY_DEFAULTED"
        for issue
        in result.issues
    )
