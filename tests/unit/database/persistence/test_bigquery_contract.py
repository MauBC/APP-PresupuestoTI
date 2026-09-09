import pytest

from database.persistence.bigquery_contract import (
    build_audit_schema,
    build_batch_schema,
    build_persistence_table_specs,
    build_staging_schema,
)


pytestmark = pytest.mark.unit


def schema_map(
    schema,
):
    return {
        field.name: (
            field.field_type,
            field.mode,
        )
        for field in schema
    }


def test_batch_bigquery_schema():
    schema = build_batch_schema()

    assert len(
        schema
    ) == 11

    fields = schema_map(
        schema
    )

    assert fields[
        "batch_id"
    ] == (
        "STRING",
        "REQUIRED",
    )

    assert fields[
        "status"
    ] == (
        "STRING",
        "REQUIRED",
    )

    assert fields[
        "completed_at"
    ] == (
        "TIMESTAMP",
        "NULLABLE",
    )

    assert fields[
        "error_message"
    ] == (
        "STRING",
        "NULLABLE",
    )

    assert fields[
        "budget_module"
    ] == (
        "STRING",
        "NULLABLE",
    )

    assert fields[
        "reverted_batch_id"
    ] == (
        "STRING",
        "NULLABLE",
    )


def test_audit_bigquery_schema():
    schema = build_audit_schema()

    assert len(
        schema
    ) == 11

    fields = schema_map(
        schema
    )

    assert fields[
        "audit_id"
    ] == (
        "STRING",
        "REQUIRED",
    )

    assert fields[
        "before_value"
    ] == (
        "STRING",
        "NULLABLE",
    )

    assert fields[
        "after_value"
    ] == (
        "STRING",
        "NULLABLE",
    )

    assert fields[
        "version_before"
    ] == (
        "INTEGER",
        "REQUIRED",
    )


def test_staging_bigquery_schema():
    schema = (
        build_staging_schema()
    )

    assert len(
        schema
    ) == 18

    fields = schema_map(
        schema
    )

    assert fields[
        "batch_id"
    ] == (
        "STRING",
        "REQUIRED",
    )

    assert fields[
        "expected_version"
    ] == (
        "INTEGER",
        "REQUIRED",
    )

    assert fields[
        "habilitado"
    ] == (
        "BOOLEAN",
        "REQUIRED",
    )

    assert fields[
        "enero_usd"
    ] == (
        "NUMERIC",
        "NULLABLE",
    )

    assert fields[
        "anio_usd"
    ] == (
        "NUMERIC",
        "NULLABLE",
    )

    assert fields[
        "staged_at"
    ] == (
        "TIMESTAMP",
        "REQUIRED",
    )


def test_three_persistence_table_specs():
    specs = (
        build_persistence_table_specs()
    )

    assert len(
        specs
    ) == 3

    names = {
        spec.table_name
        for spec in specs
    }

    assert names == {
        "presupuesto_change_batches",
        "presupuesto_audit",
        "presupuesto_change_staging",
    }
