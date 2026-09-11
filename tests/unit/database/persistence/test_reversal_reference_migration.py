from types import SimpleNamespace

import pytest
from google.cloud import bigquery

from database.migrations.reversal_reference import (
    ReversalReferenceMigrationError,
    migrate_reversal_reference,
)


pytestmark = pytest.mark.unit


class FakeJob:
    def __init__(
        self,
    ):
        self.result_called = False

    def result(
        self,
    ):
        self.result_called = True
        return ()


class FakeClient:
    def __init__(
        self,
        *,
        before_schema,
        after_schema=None,
    ):
        self.before = SimpleNamespace(
            schema=tuple(
                before_schema
            )
        )

        self.after = SimpleNamespace(
            schema=tuple(
                after_schema
                if after_schema is not None
                else before_schema
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
        job = FakeJob()

        self.query_calls.append(
            {
                "sql": sql,
                "location": location,
                "job": job,
            }
        )

        return job


def migrate(
    client,
    *,
    apply=False,
):
    return migrate_reversal_reference(
        client,
        project="project-test",
        dataset="dataset-test",
        batch_table="batches",
        location="US",
        apply=apply,
    )


def field(
    field_type="STRING",
    mode="NULLABLE",
):
    return bigquery.SchemaField(
        "reverted_batch_id",
        field_type,
        mode=mode,
    )


def test_dry_run_reports_missing_column():
    client = FakeClient(
        before_schema=(
            bigquery.SchemaField(
                "batch_id",
                "STRING",
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

    assert not (
        result.column_existed
    )

    assert (
        client.query_calls
        == []
    )


def test_dry_run_accepts_existing_column():
    client = FakeClient(
        before_schema=(
            field(),
        )
    )

    result = migrate(
        client
    )

    assert (
        result.status
        == "EXISTS"
    )

    assert (
        result.column_existed
    )


def test_invalid_existing_type_is_rejected():
    client = FakeClient(
        before_schema=(
            field(
                "INTEGER"
            ),
        )
    )

    with pytest.raises(
        ReversalReferenceMigrationError,
        match="STRING",
    ):
        migrate(
            client
        )


def test_apply_adds_and_validates_column():
    client = FakeClient(
        before_schema=(
            bigquery.SchemaField(
                "batch_id",
                "STRING",
            ),
        ),
        after_schema=(
            bigquery.SchemaField(
                "batch_id",
                "STRING",
            ),
            field(),
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

    assert not (
        result.column_existed
    )

    assert len(
        client.query_calls
    ) == 1

    assert (
        "ALTER TABLE"
        in client.query_calls[
            0
        ]["sql"]
    )

    assert (
        "ADD COLUMN"
        in client.query_calls[
            0
        ]["sql"]
    )

    assert (
        client.query_calls[
            0
        ]["location"]
        == "US"
    )


def test_apply_existing_column_is_idempotent():
    client = FakeClient(
        before_schema=(
            field(),
        ),
        after_schema=(
            field(),
        ),
    )

    result = migrate(
        client,
        apply=True,
    )

    assert (
        result.column_existed
    )

    assert (
        client.query_calls
        == []
    )
