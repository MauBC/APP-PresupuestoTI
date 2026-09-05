import pytest

from database.bootstrap.bigquery_contract import (
    BIGQUERY_STORAGE_TYPES,
    build_bigquery_schema,
    build_bootstrap_load_config,
)
from database.bootstrap.persistence_enricher import (
    FINAL_STORAGE_COLUMNS,
    TECHNICAL_COLUMNS,
)
from database.bootstrap.schema import (
    STORAGE_AMOUNT_COLUMNS,
    STORAGE_STRING_COLUMNS,
)


pytestmark = pytest.mark.unit


def test_bigquery_schema_has_67_fields():
    schema = (
        build_bigquery_schema()
    )

    assert len(schema) == 67


def test_bigquery_schema_order_matches_storage():
    schema = (
        build_bigquery_schema()
    )

    assert tuple(
        field.name
        for field in schema
    ) == FINAL_STORAGE_COLUMNS


def test_business_string_types():
    for column in (
        STORAGE_STRING_COLUMNS
    ):
        assert (
            BIGQUERY_STORAGE_TYPES[
                column
            ]
            == "STRING"
        )


def test_amount_types_are_numeric():
    for column in (
        STORAGE_AMOUNT_COLUMNS
    ):
        assert (
            BIGQUERY_STORAGE_TYPES[
                column
            ]
            == "NUMERIC"
        )


def test_technical_columns_are_required():
    schema = (
        build_bigquery_schema()
    )

    fields = {
        field.name: field
        for field in schema
    }

    for column in TECHNICAL_COLUMNS:
        assert (
            fields[
                column
            ].mode
            == "REQUIRED"
        )


def test_business_columns_are_nullable():
    schema = (
        build_bigquery_schema()
    )

    fields = {
        field.name: field
        for field in schema
    }

    assert (
        fields["pais"].mode
        == "NULLABLE"
    )

    assert (
        fields["enero_usd"].mode
        == "NULLABLE"
    )


def test_bootstrap_config_uses_explicit_schema():
    config = (
        build_bootstrap_load_config()
    )

    assert (
        config.autodetect
        is False
    )

    assert len(
        config.schema
    ) == 67


def test_bootstrap_config_uses_write_truncate():
    config = (
        build_bootstrap_load_config()
    )

    assert (
        config.write_disposition
        == "WRITE_TRUNCATE"
    )