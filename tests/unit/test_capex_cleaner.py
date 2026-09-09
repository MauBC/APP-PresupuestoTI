from decimal import Decimal

import pytest

from app.services.capex_cleaner import (
    CapexCleaningError,
    clean_capex_amount,
    clean_capex_integer,
    clean_capex_text,
)


pytestmark = pytest.mark.unit


def test_code_preserves_leading_zero():
    assert (
        clean_capex_text(
            " 04WF2EAF90 "
        )
        == "04WF2EAF90"
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
def test_blank_text_becomes_none(
    value,
):
    assert (
        clean_capex_text(
            value
        )
        is None
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
def test_blank_amount_becomes_zero(
    value,
):
    assert (
        clean_capex_amount(
            value
        )
        == Decimal("0.00")
    )


def test_numeric_amount_is_decimal():
    assert (
        clean_capex_amount(
            1250
        )
        == Decimal("1250.00")
    )


def test_decimal_amount_uses_bigquery_numeric_scale():
    result = clean_capex_amount(
        "7902.163691666668"
    )

    assert (
        result
        == Decimal(
            "7902.163691667"
        )
    )

    assert (
        result.as_tuple().exponent
        == -9
    )


def test_decimal_comma_is_supported():
    assert (
        clean_capex_amount(
            "1250,50"
        )
        == Decimal("1250.50")
    )


@pytest.mark.parametrize(
    "value",
    (
        "#N/A",
        "#NA",
        "#VALUE!",
        "#REF!",
    ),
)
def test_excel_error_is_not_silently_zero(
    value,
):
    with pytest.raises(
        CapexCleaningError,
        match="error de Excel",
    ):
        clean_capex_amount(
            value
        )


def test_negative_amount_is_rejected():
    with pytest.raises(
        CapexCleaningError,
        match="negativo",
    ):
        clean_capex_amount(
            "-1.00"
        )


def test_integer_accepts_integral_number():
    assert (
        clean_capex_integer(
            "2027.0"
        )
        == 2027
    )


def test_integer_rejects_decimal():
    with pytest.raises(
        CapexCleaningError,
        match="sin decimales",
    ):
        clean_capex_integer(
            "2.5"
        )
