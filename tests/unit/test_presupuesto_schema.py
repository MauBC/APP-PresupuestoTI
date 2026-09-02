import pytest

from app.config.presupuesto_schema import (
    AMOUNT_COLUMNS,
    EXPECTED_COLUMNS,
    EXPECTED_TYPES,
    STRING_COLUMNS,
)


@pytest.mark.unit
def test_string_column_count():
    assert len(STRING_COLUMNS) == 23


@pytest.mark.unit
def test_amount_column_count():
    assert len(AMOUNT_COLUMNS) == 39


@pytest.mark.unit
def test_total_column_count():
    assert len(EXPECTED_COLUMNS) == 62


@pytest.mark.unit
def test_columns_are_unique():
    assert len(EXPECTED_COLUMNS) == len(
        set(EXPECTED_COLUMNS)
    )


@pytest.mark.unit
def test_expected_type_count():
    assert len(EXPECTED_TYPES) == 62