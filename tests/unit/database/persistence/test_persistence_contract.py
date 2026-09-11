import pytest

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
    USD_COLUMNS,
)
from database.persistence.contract import (
    AUDIT_COLUMNS,
    AUDIT_NULLABLE_COLUMNS,
    AUDIT_TYPES,
    BATCH_COLUMNS,
    BATCH_NULLABLE_COLUMNS,
    BATCH_STATUSES,
    BATCH_TYPES,
    EDITABLE_COLUMNS,
    EDITABLE_VALUE_TYPES,
    STAGING_COLUMNS,
    STAGING_NULLABLE_COLUMNS,
    STAGING_TYPES,
)


pytestmark = pytest.mark.unit


def test_editable_columns_contract():
    assert EDITABLE_COLUMNS == (
        HABILITADO_COLUMN,
        *USD_COLUMNS,
    )

    assert len(
        EDITABLE_COLUMNS
    ) == 14


def test_editable_types_contract():
    assert (
        EDITABLE_VALUE_TYPES[
            HABILITADO_COLUMN
        ]
        == "BOOLEAN"
    )

    for column in USD_COLUMNS:
        assert (
            EDITABLE_VALUE_TYPES[
                column
            ]
            == "NUMERIC"
        )


def test_batch_contract():
    assert BATCH_COLUMNS == (
        "batch_id",
        "status",
        "actor",
        "created_at",
        "completed_at",
        "row_count",
        "field_count",
        "app_version",
        "error_message",
        "budget_module",
        "reverted_batch_id",
    )

    assert set(
        BATCH_NULLABLE_COLUMNS
    ) == {
        "completed_at",
        "app_version",
        "error_message",
        "budget_module",
        "reverted_batch_id",
    }

    assert set(
        BATCH_TYPES
    ) == set(
        BATCH_COLUMNS
    )

    assert (
        BATCH_TYPES[
            "budget_module"
        ]
        == "STRING"
    )


def test_batch_statuses():
    assert BATCH_STATUSES == (
        "PENDING",
        "APPLIED",
        "CONFLICT",
        "FAILED",
    )


def test_audit_contract():
    assert AUDIT_COLUMNS == (
        "audit_id",
        "batch_id",
        "row_id",
        "column_name",
        "value_type",
        "before_value",
        "after_value",
        "version_before",
        "version_after",
        "actor",
        "changed_at",
    )

    assert set(
        AUDIT_NULLABLE_COLUMNS
    ) == {
        "before_value",
        "after_value",
    }

    assert set(
        AUDIT_TYPES
    ) == set(
        AUDIT_COLUMNS
    )


def test_staging_contract():
    assert STAGING_COLUMNS == (
        "batch_id",
        "row_id",
        "expected_version",
        HABILITADO_COLUMN,
        *USD_COLUMNS,
        "staged_at",
        "operation",
        "insert_payload",
    )

    assert STAGING_NULLABLE_COLUMNS == (
        *USD_COLUMNS,
        "operation",
        "insert_payload",
    )

    assert set(
        STAGING_TYPES
    ) == set(
        STAGING_COLUMNS
    )
