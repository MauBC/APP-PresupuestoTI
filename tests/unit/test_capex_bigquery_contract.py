import pytest

from app.config.capex_schema import (
    CAPEX_BUSINESS_COLUMNS,
    CAPEX_EXPECTED_COLUMNS,
    CAPEX_EXPECTED_TYPES,
)
from app.config.presupuesto_schema import (
    PERSISTENCE_COLUMNS,
)
from database.bootstrap.capex_bigquery_contract import (
    build_capex_append_load_config,
    build_capex_bigquery_schema,
    build_capex_bootstrap_load_config,
)


pytestmark = pytest.mark.unit


def test_capex_bigquery_schema_has_58_fields():
    schema = (
        build_capex_bigquery_schema()
    )

    assert len(
        schema
    ) == 58

    assert tuple(
        field.name
        for field in schema
    ) == tuple(
        CAPEX_EXPECTED_COLUMNS
    )


def test_capex_bigquery_schema_types_match_contract():
    schema = (
        build_capex_bigquery_schema()
    )

    actual = {
        field.name:
            field.field_type
        for field in schema
    }

    assert actual == dict(
        CAPEX_EXPECTED_TYPES
    )


def test_only_technical_fields_are_required():
    schema = (
        build_capex_bigquery_schema()
    )

    modes = {
        field.name:
            field.mode
        for field in schema
    }

    for column in (
        PERSISTENCE_COLUMNS
    ):
        assert (
            modes[column]
            == "REQUIRED"
        )

    for column in (
        CAPEX_BUSINESS_COLUMNS
    ):
        assert (
            modes[column]
            == "NULLABLE"
        )


def test_capex_bootstrap_load_uses_explicit_schema():
    config = (
        build_capex_bootstrap_load_config()
    )

    assert (
        config.autodetect
        is False
    )

    assert (
        len(
            config.schema
        )
        == 58
    )

    assert (
        config.write_disposition
        == "WRITE_TRUNCATE"
    )


def test_capex_append_load_uses_write_append():
    config = (
        build_capex_append_load_config()
    )

    assert (
        config.autodetect
        is False
    )

    assert (
        len(
            config.schema
        )
        == 58
    )

    assert (
        config.write_disposition
        == "WRITE_APPEND"
    )
