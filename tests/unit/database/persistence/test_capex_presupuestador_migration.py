from types import SimpleNamespace

import pytest
from google.cloud import bigquery

from database.migrations.capex_presupuestador import (
    CapexPresupuestadorMigrationError,
    migrate_capex_presupuestador,
)


pytestmark = pytest.mark.unit


class FakeJob:
    def result(
        self,
    ):
        return None


class FakeClient:
    def __init__(
        self,
        *,
        schema=(),
    ):
        self.schema = list(
            schema
        )

        self.query_calls = []

    def get_table(
        self,
        table_id,
    ):
        return SimpleNamespace(
            schema=list(
                self.schema
            )
        )

    def query(
        self,
        sql,
        *,
        location=None,
    ):
        self.query_calls.append(
            {
                "sql": sql,
                "location": location,
            }
        )

        if (
            "ADD COLUMN" in sql
            and not any(
                field.name
                == "presupuestador"
                for field in self.schema
            )
        ):
            self.schema.append(
                bigquery.SchemaField(
                    "presupuestador",
                    "STRING",
                    mode="NULLABLE",
                )
            )

        return FakeJob()


def migrate(
    client,
    *,
    apply=False,
):
    return migrate_capex_presupuestador(
        client,
        project="project-test",
        dataset="dataset-test",
        table="capex_2027",
        location="US",
        apply=apply,
    )


def test_dry_run_reports_missing_column():
    client = FakeClient()

    result = migrate(
        client
    )

    assert result.status == "WOULD_ADD"
    assert not result.column_existed
    assert client.query_calls == []


def test_existing_column_is_noop():
    client = FakeClient(
        schema=(
            bigquery.SchemaField(
                "presupuestador",
                "STRING",
                mode="NULLABLE",
            ),
        )
    )

    result = migrate(
        client,
        apply=True,
    )

    assert result.status == "EXISTS"
    assert result.column_existed
    assert client.query_calls == []


def test_apply_adds_column():
    client = FakeClient()

    result = migrate(
        client,
        apply=True,
    )

    assert result.status == "MIGRATED"

    assert len(
        client.query_calls
    ) == 1

    assert (
        "ALTER TABLE"
        in client.query_calls[0]["sql"]
    )

    assert (
        "ADD COLUMN"
        in client.query_calls[0]["sql"]
    )


def test_wrong_existing_type_is_rejected():
    client = FakeClient(
        schema=(
            bigquery.SchemaField(
                "presupuestador",
                "INTEGER",
                mode="NULLABLE",
            ),
        )
    )

    with pytest.raises(
        CapexPresupuestadorMigrationError,
        match="STRING",
    ):
        migrate(
            client
        )
