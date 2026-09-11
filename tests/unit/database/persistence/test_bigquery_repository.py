from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.config.settings import settings
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from database.persistence.batch_builder import (
    build_persistence_batch,
)
from database.persistence.bigquery_repository import (
    BigQueryPersistenceError,
    BigQueryPersistenceRepository,
)
from database.persistence.staging_builder import (
    build_staging_rows,
)


pytestmark = pytest.mark.unit


FIXED_TIME = datetime(
    2026,
    9,
    7,
    18,
    0,
    tzinfo=timezone.utc,
)


class FakeQueryJob:
    def __init__(
        self,
        *,
        affected_rows=1,
        result_rows=None,
    ):
        self.num_dml_affected_rows = (
            affected_rows
        )

        self._result_rows = (
            result_rows
            if result_rows is not None
            else ()
        )

        self.result_called = False

    def result(
        self,
    ):
        self.result_called = True
        return iter(
            self._result_rows
        )


class FakeLoadJob:
    def __init__(
        self,
        output_rows,
    ):
        self.output_rows = (
            output_rows
        )

        self.result_called = False

    def result(
        self,
    ):
        self.result_called = True
        return None


class FakeBigQueryClient:
    def __init__(
        self,
    ):
        self.query_calls = []
        self.load_calls = []

        self.next_query_job = (
            FakeQueryJob()
        )

        self.next_load_job = (
            FakeLoadJob(
                output_rows=1
            )
        )

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
                "job_config": (
                    job_config
                ),
                "location": location,
            }
        )

        return self.next_query_job

    def load_table_from_json(
        self,
        rows,
        destination,
        *,
        job_config=None,
        location=None,
    ):
        self.load_calls.append(
            {
                "rows": list(rows),
                "destination": (
                    destination
                ),
                "job_config": (
                    job_config
                ),
                "location": location,
            }
        )

        return self.next_load_job


def make_source_row(
    *,
    row_id="row-1",
    version=1,
):
    row = {
        "row_id": row_id,
        "version": version,
        "habilitado": True,
    }

    for column in (
        USD_MONTH_COLUMNS
    ):
        row[column] = (
            Decimal("0.00")
        )

    row[
        "enero_usd"
    ] = Decimal(
        "100.00"
    )

    row[
        "anio_usd"
    ] = Decimal(
        "100.00"
    )

    return row


def make_batch_and_staging(
    *,
    row_id="row-1",
    version=1,
    amount="125.00",
    batch_id="batch-001",
):
    workspace = (
        PresupuestoWorkspace()
    )

    workspace.load(
        [
            make_source_row(
                row_id=row_id,
                version=version,
            )
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal(amount),
    )

    batch = (
        build_persistence_batch(
            workspace,
            actor=(
                "usuario@empresa.com"
            ),
            app_version="0.5.0",
            timestamp=FIXED_TIME,
            batch_id_factory=lambda: (
                batch_id
            ),
        )
    )

    staging = (
        build_staging_rows(
            batch,
            timestamp=FIXED_TIME,
        )
    )

    return (
        batch,
        staging,
    )


def repository(
    client=None,
):
    return (
        BigQueryPersistenceRepository(
            client
            or FakeBigQueryClient(),
            project="project-test",
            dataset="dataset_test",
            location="US",
        )
    )


def parameter_map(
    job_config,
):
    return {
        parameter.name:
            parameter.value
        for parameter
        in job_config.query_parameters
    }


def test_table_ids():
    client = (
        FakeBigQueryClient()
    )

    repo = repository(
        client
    )

    assert repo.main_table_id == (
        "project-test."
        "dataset_test."
        f"{settings.BIGQUERY_TABLE}"
    )

    assert repo.batch_table_id == (
        "project-test."
        "dataset_test."
        "presupuesto_change_batches"
    )

    assert repo.audit_table_id == (
        "project-test."
        "dataset_test."
        "presupuesto_audit"
    )

    assert repo.staging_table_id == (
        "project-test."
        "dataset_test."
        "presupuesto_change_staging"
    )


def test_insert_pending_batch_uses_parameters():
    client = (
        FakeBigQueryClient()
    )

    batch, _ = (
        make_batch_and_staging()
    )

    repo = repository(
        client
    )

    affected = (
        repo.insert_pending_batch(
            batch
        )
    )

    assert affected == 1
    assert len(
        client.query_calls
    ) == 1

    call = (
        client.query_calls[0]
    )

    assert (
        "INSERT INTO"
        in call["sql"]
    )

    assert (
        "WHERE NOT EXISTS"
        in call["sql"]
    )

    assert (
        "usuario@empresa.com"
        not in call["sql"]
    )

    params = parameter_map(
        call["job_config"]
    )

    assert (
        params["batch_id"]
        == "batch-001"
    )

    assert (
        params["status"]
        == "PENDING"
    )

    assert (
        params["budget_module"]
        == "OPEX"
    )

    assert (
        params["reverted_batch_id"]
        is None
    )

    assert (
        params["actor"]
        == "usuario@empresa.com"
    )

    assert (
        params["row_count"]
        == 1
    )

    assert (
        params["field_count"]
        == 2
    )

    assert (
        call["location"]
        == "US"
    )

    assert (
        client
        .next_query_job
        .result_called
    )


def test_non_pending_batch_is_rejected():
    from dataclasses import replace

    client = (
        FakeBigQueryClient()
    )

    batch, _ = (
        make_batch_and_staging()
    )

    batch = replace(
        batch,
        status="APPLIED",
    )

    repo = repository(
        client
    )

    with pytest.raises(
        BigQueryPersistenceError,
        match="PENDING",
    ):
        repo.insert_pending_batch(
            batch
        )

    assert (
        client.query_calls
        == []
    )


def test_clear_staging_uses_batch_parameter():
    client = (
        FakeBigQueryClient()
    )

    repo = repository(
        client
    )

    affected = (
        repo.clear_staging(
            "batch-001"
        )
    )

    assert affected == 1
    assert len(
        client.query_calls
    ) == 1

    call = (
        client.query_calls[0]
    )

    assert (
        "DELETE FROM"
        in call["sql"]
    )

    params = parameter_map(
        call["job_config"]
    )

    assert (
        params["batch_id"]
        == "batch-001"
    )


def test_load_staging_uses_bulk_append():
    client = (
        FakeBigQueryClient()
    )

    client.next_load_job = (
        FakeLoadJob(
            output_rows=1
        )
    )

    _, staging = (
        make_batch_and_staging()
    )

    repo = repository(
        client
    )

    count = (
        repo.load_staging_rows(
            staging
        )
    )

    assert count == 1

    assert len(
        client.load_calls
    ) == 1

    call = (
        client.load_calls[0]
    )

    assert call[
        "destination"
    ] == (
        "project-test."
        "dataset_test."
        "presupuesto_change_staging"
    )

    assert (
        call[
            "job_config"
        ].write_disposition
        == "WRITE_APPEND"
    )

    assert len(
        call[
            "job_config"
        ].schema
    ) == 20

    record = (
        call["rows"][0]
    )

    assert (
        record["batch_id"]
        == "batch-001"
    )

    assert (
        record["row_id"]
        == "row-1"
    )

    assert (
        record["expected_version"]
        == 1
    )

    assert (
        record["enero_usd"]
        == "125.00"
    )

    assert (
        record["anio_usd"]
        == "125.00"
    )

    assert isinstance(
        record["staged_at"],
        str,
    )

    assert (
        "_session_row_id"
        not in record
    )

    assert (
        client
        .next_load_job
        .result_called
    )


def test_replace_staging_deletes_before_load():
    client = (
        FakeBigQueryClient()
    )

    _, staging = (
        make_batch_and_staging()
    )

    repo = repository(
        client
    )

    count = (
        repo.replace_staging_rows(
            staging
        )
    )

    assert count == 1
    assert len(
        client.query_calls
    ) == 1
    assert len(
        client.load_calls
    ) == 1

    assert (
        "DELETE FROM"
        in client
        .query_calls[0]["sql"]
    )


def test_empty_staging_is_rejected():
    client = (
        FakeBigQueryClient()
    )

    repo = repository(
        client
    )

    with pytest.raises(
        BigQueryPersistenceError,
        match="No existen filas",
    ):
        repo.load_staging_rows(
            ()
        )

    assert (
        client.load_calls
        == []
    )


def test_mixed_batches_are_rejected():
    client = (
        FakeBigQueryClient()
    )

    _, staging_a = (
        make_batch_and_staging(
            row_id="row-a",
            batch_id="batch-a",
        )
    )

    _, staging_b = (
        make_batch_and_staging(
            row_id="row-b",
            batch_id="batch-b",
        )
    )

    repo = repository(
        client
    )

    with pytest.raises(
        BigQueryPersistenceError,
        match="mismo batch",
    ):
        repo.load_staging_rows(
            (
                staging_a[0],
                staging_b[0],
            )
        )


def test_duplicate_row_id_is_rejected():
    client = (
        FakeBigQueryClient()
    )

    _, staging = (
        make_batch_and_staging()
    )

    repo = repository(
        client
    )

    with pytest.raises(
        BigQueryPersistenceError,
        match="duplicados",
    ):
        repo.load_staging_rows(
            (
                staging[0],
                staging[0],
            )
        )


def test_count_staging_rows():
    client = (
        FakeBigQueryClient()
    )

    client.next_query_job = (
        FakeQueryJob(
            affected_rows=None,
            result_rows=[
                {
                    "row_count": 7,
                }
            ],
        )
    )

    repo = repository(
        client
    )

    assert (
        repo.count_staging_rows(
            "batch-001"
        )
        == 7
    )

    call = (
        client.query_calls[0]
    )

    assert (
        "COUNT(*)"
        in call["sql"]
    )

    assert (
        parameter_map(
            call["job_config"]
        )["batch_id"]
        == "batch-001"
    )


def test_decimal_and_timestamp_serialization():
    _, staging = (
        make_batch_and_staging()
    )

    record = (
        BigQueryPersistenceRepository
        ._staging_record(
            staging[0]
        )
    )

    assert (
        record["enero_usd"]
        == "125.00"
    )

    assert (
        record["staged_at"]
        == FIXED_TIME.isoformat()
    )


def test_missing_project_is_rejected():
    with pytest.raises(
        BigQueryPersistenceError,
        match="project",
    ):
        BigQueryPersistenceRepository(
            FakeBigQueryClient(),
            project=" ",
            dataset="dataset_test",
            location="US",
        )


def test_stage_rows_uses_query_for_small_batch(
    monkeypatch,
):
    repo = repository()

    _, staging = (
        make_batch_and_staging()
    )

    calls = []

    monkeypatch.setattr(
        repo,
        "insert_staging_rows",
        lambda rows: (
            calls.append(
                (
                    "query",
                    len(tuple(rows)),
                )
            )
            or len(tuple(rows))
        ),
    )

    monkeypatch.setattr(
        repo,
        "load_staging_rows",
        lambda rows: (
            calls.append(
                (
                    "load",
                    len(tuple(rows)),
                )
            )
            or len(tuple(rows))
        ),
    )

    count = repo.stage_rows(
        staging
    )

    assert count == 1

    assert calls == [
        (
            "query",
            1,
        )
    ]


def test_stage_rows_uses_load_job_for_large_batch(
    monkeypatch,
):
    from dataclasses import replace

    repo = repository()

    _, staging = (
        make_batch_and_staging()
    )

    rows = tuple(
        replace(
            staging[0],
            row_id=f"row-{index}",
        )
        for index in range(
            51
        )
    )

    calls = []

    monkeypatch.setattr(
        repo,
        "insert_staging_rows",
        lambda values: (
            calls.append(
                (
                    "query",
                    len(tuple(values)),
                )
            )
            or len(tuple(values))
        ),
    )

    monkeypatch.setattr(
        repo,
        "load_staging_rows",
        lambda values: (
            calls.append(
                (
                    "load",
                    len(tuple(values)),
                )
            )
            or len(tuple(values))
        ),
    )

    count = repo.stage_rows(
        rows
    )

    assert count == 51

    assert calls == [
        (
            "load",
            51,
        )
    ]


def test_query_parameter_type_aliases():
    repo = repository()

    assert (
        repo._query_parameter_type(
            "INTEGER"
        )
        == "INT64"
    )

    assert (
        repo._query_parameter_type(
            "BOOLEAN"
        )
        == "BOOL"
    )

    assert (
        repo._query_parameter_type(
            "NUMERIC"
        )
        == "NUMERIC"
    )

    assert (
        repo._query_parameter_type(
            "TIMESTAMP"
        )
        == "TIMESTAMP"
    )
