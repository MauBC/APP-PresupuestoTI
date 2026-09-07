import pytest

from app.config.presupuesto_schema import (
    EXPECTED_COLUMNS,
    EXPECTED_TYPES,
)
from app.services.bigquery_service import BigQueryService


pytestmark = pytest.mark.integration


def test_presupuesto_schema_matches_contract():
    service = BigQueryService()

    table = service.get_table()

    actual_types = {
        field.name: field.field_type
        for field in table.schema
    }

    expected_columns = set(EXPECTED_COLUMNS)
    actual_columns = set(actual_types)

    missing_columns = (
        expected_columns - actual_columns
    )

    unexpected_columns = (
        actual_columns - expected_columns
    )

    assert not missing_columns, (
        "Faltan columnas requeridas: "
        f"{sorted(missing_columns)}"
    )

    assert not unexpected_columns, (
        "Existen columnas no esperadas: "
        f"{sorted(unexpected_columns)}"
    )

    wrong_types = {
        column: {
            "expected": expected_type,
            "actual": actual_types[column],
        }
        for column, expected_type
        in EXPECTED_TYPES.items()
        if actual_types.get(column) != expected_type
    }

    assert not wrong_types, (
        "Existen columnas con tipo incorrecto: "
        f"{wrong_types}"
    )