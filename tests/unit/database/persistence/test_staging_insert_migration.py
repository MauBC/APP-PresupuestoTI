
from types import SimpleNamespace

import pytest
from google.cloud import bigquery

from database.migrations.staging_insert_support import (
    StagingInsertMigrationError,
    migrate_staging_insert_support,
)


pytestmark = pytest.mark.unit


class FakeJob:
    def result(
        self,
    ):
        return ()


class FakeClient:
    def __init__(
        self,
        *,
        before,
        after=None,
    ):
        self.before = SimpleNamespace(
            schema=tuple(
                before
            )
        )

        self.after = SimpleNamespace(
            schema=tuple(
                after
                if after is not None
                else before
            )
        )

        self.get_calls = 0
        self.query_calls = []

    def get_table(
        self,
        table_id,
    ):
        self.get_calls += 1

        if self.get_calls == 1:
            return self.before

        return self.after

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

        return FakeJob()


def field(
    name,
    field_type="STRING",
    mode="NULLABLE",
):
    return bigquery.SchemaField(
        name,
        field_type,
        mode=mode,
    )


def migrate(
    client,
    *,
    apply=False,
):
    return (
        migrate_staging_insert_support(
            client,
            project="project",
            dataset="dataset",
            staging_table="staging",
            location="US",
            apply=apply,
        )
    )


def test_dry_run_reports_two_columns():
    client = FakeClient(
        before=(
            field(
                "batch_id",
                "STRING",
                "REQUIRED",
            ),
        )
    )

    result = migrate(
        client
    )

    assert (
        result.status
        == "WOULD_ADD"
    )

    assert result.added_columns == (
        "operation",
        "insert_payload",
    )

    assert client.query_calls == []


def test_existing_columns_are_idempotent():
    client = FakeClient(
        before=(
            field("operation"),
            field("insert_payload"),
        )
    )

    result = migrate(
        client,
        apply=True,
    )

    assert (
        result.status
        == "EXISTS"
    )

    assert client.query_calls == []


def test_apply_adds_columns_in_order():
    client = FakeClient(
        before=(
            field(
                "batch_id",
                "STRING",
                "REQUIRED",
            ),
        ),
        after=(
            field(
                "batch_id",
                "STRING",
                "REQUIRED",
            ),
            field("operation"),
            field("insert_payload"),
        ),
    )

    result = migrate(
        client,
        apply=True,
    )

    assert (
        result.status
        == "MIGRATED"
    )

    assert len(
        client.query_calls
    ) == 2

    assert (
        "`operation` STRING"
        in client
        .query_calls[0]["sql"]
    )

    assert (
        "`insert_payload` STRING"
        in client
        .query_calls[1]["sql"]
    )


def test_invalid_existing_type_is_rejected():
    client = FakeClient(
        before=(
            field(
                "operation",
                "INTEGER",
            ),
        )
    )

    with pytest.raises(
        StagingInsertMigrationError,
        match="STRING",
    ):
        migrate(
            client
        )
