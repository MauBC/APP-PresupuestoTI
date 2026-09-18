from types import SimpleNamespace

import pytest
from google.api_core.exceptions import (
    NotFound,
)

from database.bootstrap.capex_bigquery_contract import (
    build_capex_bigquery_schema,
)
from database.migrations.capex_main_table import (
    CapexMainTableError,
    build_capex_table_id,
    capex_schema_matches,
    ensure_capex_main_table,
)


pytestmark = pytest.mark.unit


class FakeClient:
    def __init__(
        self,
        *,
        table=None,
        dataset_location="US",
    ):
        self.table = table
        self.dataset_location = (
            dataset_location
        )
        self.created_tables = []

    def get_dataset(
        self,
        dataset_id,
    ):
        return SimpleNamespace(
            dataset_id=dataset_id,
            location=(
                self.dataset_location
            ),
        )

    def get_table(
        self,
        table_id,
    ):
        if self.table is None:
            raise NotFound(
                "not found"
            )

        return self.table

    def create_table(
        self,
        table,
    ):
        self.created_tables.append(
            table
        )

        self.table = table

        return table


def make_existing_table(
    *,
    schema=None,
):
    return SimpleNamespace(
        schema=(
            list(
                build_capex_bigquery_schema()
            )
            if schema is None
            else schema
        )
    )


def test_build_capex_table_id():
    assert (
        build_capex_table_id(
            project="proyecto-yvette",
            dataset="presupuesto_ti",
            table="capex_2027",
        )
        ==
        (
            "proyecto-yvette."
            "presupuesto_ti."
            "capex_2027"
        )
    )


def test_capex_schema_matches_expected():
    assert capex_schema_matches(
        build_capex_bigquery_schema()
    )


def test_capex_schema_match_ignores_field_order():
    schema = list(
        build_capex_bigquery_schema()
    )

    reordered = tuple(
        reversed(
            schema
        )
    )

    assert capex_schema_matches(
        reordered
    )


def test_dry_run_does_not_create_table():
    client = FakeClient()

    result = (
        ensure_capex_main_table(
            client,
            project="proyecto-yvette",
            dataset="presupuesto_ti",
            table="capex_2027",
            location="US",
            apply=False,
        )
    )

    assert not result.exists
    assert not result.created

    assert (
        client.created_tables
        == []
    )


def test_apply_creates_missing_table():
    client = FakeClient()

    result = (
        ensure_capex_main_table(
            client,
            project="proyecto-yvette",
            dataset="presupuesto_ti",
            table="capex_2027",
            location="US",
            apply=True,
        )
    )

    assert result.exists
    assert result.created
    assert result.schema_matches
    assert result.column_count == 58

    assert (
        len(
            client.created_tables
        )
        == 1
    )


def test_existing_matching_table_is_noop():
    client = FakeClient(
        table=(
            make_existing_table()
        )
    )

    result = (
        ensure_capex_main_table(
            client,
            project="proyecto-yvette",
            dataset="presupuesto_ti",
            table="capex_2027",
            location="US",
            apply=True,
        )
    )

    assert result.exists
    assert not result.created
    assert result.schema_matches

    assert (
        client.created_tables
        == []
    )


def test_existing_wrong_schema_is_rejected():
    wrong_schema = list(
        build_capex_bigquery_schema()
    )[:-1]

    client = FakeClient(
        table=(
            make_existing_table(
                schema=wrong_schema
            )
        )
    )

    with pytest.raises(
        CapexMainTableError,
        match="schema no coincide",
    ):
        ensure_capex_main_table(
            client,
            project="proyecto-yvette",
            dataset="presupuesto_ti",
            table="capex_2027",
            location="US",
            apply=True,
        )


def test_location_mismatch_is_rejected():
    client = FakeClient(
        dataset_location="EU",
    )

    with pytest.raises(
        CapexMainTableError,
        match="location",
    ):
        ensure_capex_main_table(
            client,
            project="proyecto-yvette",
            dataset="presupuesto_ti",
            table="capex_2027",
            location="US",
            apply=True,
        )
