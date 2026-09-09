import pytest

from app.config.capex_schema import (
    CAPEX_AMOUNT_COLUMNS,
    CAPEX_BUSINESS_COLUMNS,
    CAPEX_EXPECTED_COLUMNS,
    CAPEX_EXPECTED_TYPES,
    CAPEX_INTEGER_COLUMNS,
    CAPEX_ML_MONTH_COLUMNS,
    CAPEX_RAW_TO_INTERNAL,
    CAPEX_STRING_COLUMNS,
    CAPEX_USD_MONTH_COLUMNS,
)


pytestmark = pytest.mark.unit


def test_capex_has_50_business_columns():
    assert (
        len(
            CAPEX_BUSINESS_COLUMNS
        )
        == 50
    )

    assert (
        len(
            set(
                CAPEX_BUSINESS_COLUMNS
            )
        )
        == 50
    )


def test_capex_type_groups_cover_contract():
    assert (
        len(
            CAPEX_STRING_COLUMNS
        )
        == 22
    )

    assert (
        len(
            CAPEX_INTEGER_COLUMNS
        )
        == 2
    )

    assert (
        len(
            CAPEX_AMOUNT_COLUMNS
        )
        == 26
    )

    assert (
        set(
            CAPEX_BUSINESS_COLUMNS
        )
        ==
        (
            set(
                CAPEX_STRING_COLUMNS
            )
            |
            set(
                CAPEX_INTEGER_COLUMNS
            )
            |
            set(
                CAPEX_AMOUNT_COLUMNS
            )
        )
    )


def test_capex_has_12_months_per_currency():
    assert (
        len(
            CAPEX_ML_MONTH_COLUMNS
        )
        == 12
    )

    assert (
        len(
            CAPEX_USD_MONTH_COLUMNS
        )
        == 12
    )


def test_excel_mapping_has_50_headers():
    assert (
        len(
            CAPEX_RAW_TO_INTERNAL
        )
        == 50
    )

    assert (
        set(
            CAPEX_RAW_TO_INTERNAL
            .values()
        )
        ==
        set(
            CAPEX_BUSINESS_COLUMNS
        )
    )


def test_future_bigquery_contract_has_57_columns():
    assert (
        len(
            CAPEX_EXPECTED_COLUMNS
        )
        == 57
    )

    assert (
        len(
            CAPEX_EXPECTED_TYPES
        )
        == 57
    )


def test_code_columns_are_strings():
    assert (
        CAPEX_EXPECTED_TYPES[
            "codigo_cebe"
        ]
        == "STRING"
    )

    assert (
        CAPEX_EXPECTED_TYPES[
            "codigo_ceco"
        ]
        == "STRING"
    )


def test_financial_columns_are_numeric():
    assert all(
        CAPEX_EXPECTED_TYPES[
            column
        ]
        == "NUMERIC"
        for column
        in CAPEX_AMOUNT_COLUMNS
    )
