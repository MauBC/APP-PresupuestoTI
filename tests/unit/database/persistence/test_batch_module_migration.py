from types import SimpleNamespace

import pytest
from google.cloud import bigquery

from database.migrations.batch_module import (
    BatchModuleMigrationError,
    migrate_batch_module,
)


pytestmark = pytest.mark.unit


class FakeJob:
    def __init__(
        self,
        *,
        rows=(),
        affected_rows=None,
    ):
        self._rows = tuple(
            rows
        )

        self.num_dml_affected_rows = (
            affected_rows
        )

        self.result_called = False

    def result(
        self,
    ):
        self.result_called = True

        return iter(
            self._rows
        )


class FakeClient:
    def __init__(
        self,
        *,
        schema,
        jobs=(),
    ):
        self.table = SimpleNamespace(
            schema=tuple(
                schema
            )
        )

        self.jobs = list(
            jobs
        )

        self.get_table_calls = []
        self.query_calls = []

    def get_table(
        self,
        table_id,
    ):
        self.get_table_calls.append(
            table_id
        )

        return self.table

    def query(
        self,
        sql,
        *,
        job_config=None,
        location=None,
    ):
        self.query_calls.append(
            {
                "sql": sql,
                "job_config":
                    job_config,
                "location":
                    location,
            }
        )

        return self.jobs.pop(
            0
        )


def migrate(
    client,
    *,
    apply=False,
):
    return migrate_batch_module(
        client,
        project="project-test",
        dataset="dataset-test",
        batch_table="batches",
        location="US",
        apply=apply,
    )


def test_dry_run_reports_missing_column():
    client = FakeClient(
        schema=(
            bigquery.SchemaField(
                "batch_id",
                "STRING",
                mode="REQUIRED",
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

    assert result.updated_rows == 0

    assert (
        client.query_calls
        == []
    )


def test_dry_run_accepts_existing_column():
    client = FakeClient(
        schema=(
            bigquery.SchemaField(
                "budget_module",
                "STRING",
                mode="NULLABLE",
            ),
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

    assert (
        client.query_calls
        == []
    )


def test_wrong_existing_type_is_rejected():
    client = FakeClient(
        schema=(
            bigquery.SchemaField(
                "budget_module",
                "INTEGER",
                mode="NULLABLE",
            ),
        )
    )

    with pytest.raises(
        BatchModuleMigrationError,
        match="STRING",
    ):
        migrate(
            client
        )


def test_apply_adds_column_and_backfills():
    alter_job = FakeJob()

    update_job = FakeJob(
        affected_rows=12
    )

    validation_job = FakeJob(
        rows=(
            {
                "missing_rows": 0,
                "invalid_rows": 0,
            },
        )
    )

    client = FakeClient(
        schema=(
            bigquery.SchemaField(
                "batch_id",
                "STRING",
                mode="REQUIRED",
            ),
        ),
        jobs=(
            alter_job,
            update_job,
            validation_job,
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

    assert result.updated_rows == 12

    assert len(
        client.query_calls
    ) == 3

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
        "UPDATE"
        in client.query_calls[
            1
        ]["sql"]
    )

    parameters = {
        parameter.name:
            parameter.value
        for parameter
        in client.query_calls[
            1
        ][
            "job_config"
        ].query_parameters
    }

    assert (
        parameters[
            "default_module"
        ]
        == "OPEX"
    )

    assert (
        "COUNTIF"
        in client.query_calls[
            2
        ]["sql"]
    )


def test_apply_existing_column_skips_alter():
    update_job = FakeJob(
        affected_rows=3
    )

    validation_job = FakeJob(
        rows=(
            {
                "missing_rows": 0,
                "invalid_rows": 0,
            },
        )
    )

    client = FakeClient(
        schema=(
            bigquery.SchemaField(
                "budget_module",
                "STRING",
                mode="NULLABLE",
            ),
        ),
        jobs=(
            update_job,
            validation_job,
        ),
    )

    result = migrate(
        client,
        apply=True,
    )

    assert (
        result.column_existed
    )

    assert result.updated_rows == 3

    assert len(
        client.query_calls
    ) == 2

    assert (
        "ALTER TABLE"
        not in client.query_calls[
            0
        ]["sql"]
    )


def test_invalid_values_are_rejected():
    update_job = FakeJob(
        affected_rows=0
    )

    validation_job = FakeJob(
        rows=(
            {
                "missing_rows": 0,
                "invalid_rows": 2,
            },
        )
    )

    client = FakeClient(
        schema=(
            bigquery.SchemaField(
                "budget_module",
                "STRING",
                mode="NULLABLE",
            ),
        ),
        jobs=(
            update_job,
            validation_job,
        ),
    )

    with pytest.raises(
        BatchModuleMigrationError,
        match="no reconocidos",
    ):
        migrate(
            client,
            apply=True,
        )
