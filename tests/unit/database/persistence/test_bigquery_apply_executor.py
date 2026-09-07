import pytest

from database.persistence.bigquery_repository import (
    BigQueryPersistenceError,
    BigQueryPersistenceRepository,
)


pytestmark = pytest.mark.unit


class FakeJob:
    def __init__(
        self,
        *,
        rows=(),
        error=None,
    ):
        self._rows = rows
        self._error = error
        self.result_called = False

    def result(
        self,
    ):
        self.result_called = True

        if self._error is not None:
            raise self._error

        return iter(
            self._rows
        )


class FakeClient:
    def __init__(
        self,
        responses,
    ):
        self.responses = list(
            responses
        )

        self.calls = []

    def query(
        self,
        sql,
        *,
        job_config=None,
        location=None,
    ):
        self.calls.append(
            {
                "sql": sql,
                "job_config": job_config,
                "location": location,
            }
        )

        response = self.responses.pop(
            0
        )

        if isinstance(
            response,
            Exception,
        ):
            raise response

        return response


def make_repository(
    client,
):
    return BigQueryPersistenceRepository(
        client,
        project="project-test",
        dataset="dataset-test",
        location="US",
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


def test_applied_result_is_parsed():
    job = FakeJob(
        rows=[
            {
                "status": "APPLIED",
                "row_count": 2,
                "field_count": 4,
                "row_id": None,
                "expected_version": None,
                "current_version": None,
                "error_message": None,
            }
        ]
    )

    client = FakeClient(
        [job]
    )

    result = (
        make_repository(
            client
        )
        .apply_staged_batch(
            "batch-001",
            "actor@test.com",
        )
    )

    assert result.status == "APPLIED"
    assert result.is_applied
    assert result.row_count == 2
    assert result.field_count == 4
    assert result.conflicts == ()

    assert len(
        client.calls
    ) == 1

    call = client.calls[0]

    assert (
        "BEGIN TRANSACTION"
        in call["sql"]
    )

    assert (
        "MERGE "
        in call["sql"]
    )

    assert (
        "actor@test.com"
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
        params["actor"]
        == "actor@test.com"
    )

    assert (
        call["location"]
        == "US"
    )

    assert job.result_called


def test_conflict_result_is_parsed():
    job = FakeJob(
        rows=[
            {
                "status": "CONFLICT",
                "row_count": 2,
                "field_count": 4,
                "row_id": "row-a",
                "expected_version": 1,
                "current_version": 2,
                "error_message": None,
            },
            {
                "status": "CONFLICT",
                "row_count": 2,
                "field_count": 4,
                "row_id": "row-b",
                "expected_version": 3,
                "current_version": None,
                "error_message": None,
            },
        ]
    )

    client = FakeClient(
        [job]
    )

    result = (
        make_repository(
            client
        )
        .apply_staged_batch(
            "batch-001",
            "actor@test.com",
        )
    )

    assert result.status == "CONFLICT"
    assert result.has_conflicts
    assert len(
        result.conflicts
    ) == 2

    first = result.conflicts[0]
    second = result.conflicts[1]

    assert first.row_id == "row-a"
    assert first.expected_version == 1
    assert first.current_version == 2

    assert second.row_id == "row-b"
    assert second.expected_version == 3
    assert second.current_version is None

    assert len(
        client.calls
    ) == 1


def test_failed_result_marks_batch_failed():
    transaction_job = FakeJob(
        rows=[
            {
                "status": "FAILED",
                "row_count": 1,
                "field_count": 2,
                "row_id": None,
                "expected_version": None,
                "current_version": None,
                "error_message": (
                    "Synthetic transaction failure"
                ),
            }
        ]
    )

    mark_failed_job = (
        FakeJob()
    )

    client = FakeClient(
        [
            transaction_job,
            mark_failed_job,
        ]
    )

    result = (
        make_repository(
            client
        )
        .apply_staged_batch(
            "batch-001",
            "actor@test.com",
        )
    )

    assert result.status == "FAILED"

    assert (
        result.error_message
        == "Synthetic transaction failure"
    )

    assert len(
        client.calls
    ) == 2

    failed_call = (
        client.calls[1]
    )

    assert (
        "status = 'FAILED'"
        in failed_call["sql"]
    )

    params = parameter_map(
        failed_call[
            "job_config"
        ]
    )

    assert (
        params["batch_id"]
        == "batch-001"
    )

    assert (
        params["error_message"]
        == "Synthetic transaction failure"
    )


def test_query_submission_failure_is_unconfirmed():
    client = FakeClient(
        [
            RuntimeError(
                "network failure"
            )
        ]
    )

    with pytest.raises(
        BigQueryPersistenceError,
        match="No se pudo confirmar",
    ):
        make_repository(
            client
        ).apply_staged_batch(
            "batch-001",
            "actor@test.com",
        )

    assert len(
        client.calls
    ) == 1


def test_query_result_failure_is_unconfirmed():
    job = FakeJob(
        error=RuntimeError(
            "job result failure"
        )
    )

    client = FakeClient(
        [job]
    )

    with pytest.raises(
        BigQueryPersistenceError,
        match="No se pudo confirmar",
    ):
        make_repository(
            client
        ).apply_staged_batch(
            "batch-001",
            "actor@test.com",
        )

    assert job.result_called

    assert len(
        client.calls
    ) == 1


def test_empty_transaction_result_is_rejected():
    client = FakeClient(
        [
            FakeJob(
                rows=[]
            )
        ]
    )

    with pytest.raises(
        BigQueryPersistenceError,
        match="no devolvio",
    ):
        make_repository(
            client
        ).apply_staged_batch(
            "batch-001",
            "actor@test.com",
        )


def test_unknown_transaction_status_is_rejected():
    client = FakeClient(
        [
            FakeJob(
                rows=[
                    {
                        "status": "UNKNOWN",
                        "row_count": 1,
                        "field_count": 1,
                        "row_id": None,
                        "expected_version": None,
                        "current_version": None,
                        "error_message": None,
                    }
                ]
            )
        ]
    )

    with pytest.raises(
        BigQueryPersistenceError,
        match="no reconocido",
    ):
        make_repository(
            client
        ).apply_staged_batch(
            "batch-001",
            "actor@test.com",
        )


def test_empty_actor_is_rejected_before_query():
    client = FakeClient(
        []
    )

    with pytest.raises(
        BigQueryPersistenceError,
        match="actor",
    ):
        make_repository(
            client
        ).apply_staged_batch(
            "batch-001",
            "   ",
        )

    assert client.calls == []
