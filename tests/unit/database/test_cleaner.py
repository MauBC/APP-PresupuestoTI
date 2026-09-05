from decimal import Decimal

import pandas as pd
import pytest

from app.config.presupuesto_schema import (
    AMOUNT_COLUMNS,
    LEGACY_EXPECTED_COLUMNS,
    STRING_COLUMNS,
)
from database.bootstrap.cleaner import (
    CleaningError,
    clean_dataframe,
)


pytestmark = pytest.mark.unit


def make_valid_dataframe():
    row = {
        column: ""
        for column
        in LEGACY_EXPECTED_COLUMNS
    }

    row.update(
        {
            "pais": "PERU",
            "numero_cuenta": "12345",
            "enero_usd": "100.25",
            "febrero_usd": "-",
            "anio_usd": "100.25",
        }
    )

    return pd.DataFrame(
        [row]
    )


def test_clean_valid_dataframe():
    result = clean_dataframe(
        make_valid_dataframe()
    )

    assert result.is_valid

    assert tuple(
        result.dataframe.columns
    ) == LEGACY_EXPECTED_COLUMNS

    assert result.stats.row_count == 1


def test_missing_column_is_rejected():
    dataframe = (
        make_valid_dataframe()
        .drop(
            columns=["pais"]
        )
    )

    with pytest.raises(
        CleaningError,
        match="pais",
    ):
        clean_dataframe(
            dataframe
        )


def test_extra_column_is_reported_and_removed():
    dataframe = (
        make_valid_dataframe()
    )

    dataframe[
        "columna_extra"
    ] = "ABC"

    result = clean_dataframe(
        dataframe
    )

    assert result.extra_columns == (
        "columna_extra",
    )

    assert (
        "columna_extra"
        not in result.dataframe.columns
    )


def test_column_names_are_normalized():
    dataframe = (
        make_valid_dataframe()
    )

    dataframe.columns = [
        column.upper()
        for column
        in dataframe.columns
    ]

    result = clean_dataframe(
        dataframe
    )

    assert "pais" in (
        result.dataframe.columns
    )

    assert "anio_usd" in (
        result.dataframe.columns
    )


def test_blank_string_becomes_none():
    dataframe = (
        make_valid_dataframe()
    )

    dataframe.loc[
        0,
        "proveedor",
    ] = "   "

    result = clean_dataframe(
        dataframe
    )

    assert (
        result.dataframe.loc[
            0,
            "proveedor",
        ]
        is None
    )


def test_numeric_string_dimension_loses_dot_zero():
    dataframe = (
        make_valid_dataframe()
    )

    dataframe.loc[
        0,
        "numero_cuenta",
    ] = "12345.0"

    result = clean_dataframe(
        dataframe
    )

    assert (
        result.dataframe.loc[
            0,
            "numero_cuenta",
        ]
        == "12345"
    )


def test_dash_amount_becomes_zero():
    result = clean_dataframe(
        make_valid_dataframe()
    )

    assert (
        result.dataframe.loc[
            0,
            "febrero_usd",
        ]
        == Decimal("0")
    )

    assert result.stats.dash_count == 1


def test_empty_amount_becomes_none():
    result = clean_dataframe(
        make_valid_dataframe()
    )

    assert (
        result.dataframe.loc[
            0,
            "marzo_usd",
        ]
        is None
    )


def test_amount_with_commas_is_decimal():
    dataframe = (
        make_valid_dataframe()
    )

    dataframe.loc[
        0,
        "enero_usd",
    ] = "1,234.56"

    result = clean_dataframe(
        dataframe
    )

    assert (
        result.dataframe.loc[
            0,
            "enero_usd",
        ]
        == Decimal("1234.56")
    )


def test_invalid_amount_creates_issue():
    dataframe = (
        make_valid_dataframe()
    )

    dataframe.loc[
        0,
        "enero_usd",
    ] = "NO ES NUMERO"

    result = clean_dataframe(
        dataframe
    )

    assert not result.is_valid
    assert result.stats.error_count == 1

    issue = result.issues[0]

    assert issue.row_number == 2
    assert issue.column == "enero_usd"


def test_original_dataframe_is_not_modified():
    dataframe = (
        make_valid_dataframe()
    )

    original = dataframe.copy(
        deep=True
    )

    clean_dataframe(
        dataframe
    )

    pd.testing.assert_frame_equal(
        dataframe,
        original,
    )


def test_source_schema_counts():
    assert len(STRING_COLUMNS) == 23
    assert len(AMOUNT_COLUMNS) == 39

    assert (
        len(LEGACY_EXPECTED_COLUMNS)
        == 62
    )