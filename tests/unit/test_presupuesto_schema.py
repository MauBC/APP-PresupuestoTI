import pytest

from app.config.presupuesto_schema import (
    AMOUNT_COLUMNS,
    EXPECTED_COLUMNS,
    EXPECTED_TYPES,
    LEGACY_EXPECTED_COLUMNS,
    PERSISTENCE_COLUMNS,
    PERSISTENCE_TYPES,
    STRING_COLUMNS,
)


@pytest.mark.unit
def test_string_column_count():
    assert len(STRING_COLUMNS) == 23


@pytest.mark.unit
def test_amount_column_count():
    assert len(AMOUNT_COLUMNS) == 39


@pytest.mark.unit
def test_legacy_column_count():
    assert len(
        LEGACY_EXPECTED_COLUMNS
    ) == 62


@pytest.mark.unit
def test_persistence_column_count():
    assert len(
        PERSISTENCE_COLUMNS
    ) == 7


@pytest.mark.unit
def test_total_column_count():
    assert len(EXPECTED_COLUMNS) == 69


@pytest.mark.unit
def test_columns_are_unique():
    assert len(EXPECTED_COLUMNS) == len(
        set(EXPECTED_COLUMNS)
    )


@pytest.mark.unit
def test_expected_type_count():
    assert len(EXPECTED_TYPES) == 69


@pytest.mark.unit
def test_persistence_types():
    assert PERSISTENCE_TYPES == {
        "row_id": "STRING",
        "habilitado": "BOOLEAN",
        "version": "INTEGER",
        "created_at": "TIMESTAMP",
        "created_by": "STRING",
        "updated_at": "TIMESTAMP",
        "updated_by": "STRING",
    }