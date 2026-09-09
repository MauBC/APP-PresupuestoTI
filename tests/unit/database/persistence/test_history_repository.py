from datetime import (
    datetime,
    timezone,
)

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
)
from database.persistence.bigquery_repository import (
    BigQueryPersistenceError,
    BigQueryPersistenceRepository,
)


pytestmark = pytest.mark.unit


CREATED_AT = datetime(
    2026,
    9,
    8,
    18,
    0,
    tzinfo=timezone.utc,
)

COMPLETED_AT = datetime(
    2026,
    9,
    8,
    18,
    1,
    tzinfo=timezone.utc,
)


class FakeJob:
    def __init__(
        self,
        rows=(),
    ):
        self._rows = tuple(
            rows
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
        rows=(),
    ):
        self.job = FakeJob(
            rows
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
                "job_config":
                    job_config,
                "location":
                    location,
            }
        )

        return self.job


def repository(
    client,
    *,
    module_config=None,
):
    kwargs = {}

    if module_config is not None:
        kwargs[
            "module_config"
        ] = module_config

    return (
        BigQueryPersistenceRepository(
            client,
            project="project-test",
            dataset="dataset-test",
            location="US",
            **kwargs,
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


def make_history_row(
    *,
    batch_id="batch-001",
    status="APPLIED",
    module="OPEX",
):
    return {
        "batch_id": batch_id,
        "status": status,
        "actor": "RANSA\\usuario",
        "created_at": CREATED_AT,
        "completed_at": COMPLETED_AT,
        "row_count": 3,
        "field_count": 7,
        "app_version": "0.5.0",
        "error_message": None,
        "budget_module": module,
    }


def test_list_batches_defaults_to_applied_opex():
    client = FakeClient(
        [
            make_history_row()
        ]
    )

    result = (
        repository(client)
        .list_batches(
            limit=25,
            offset=50,
        )
    )

    assert len(result) == 1

    batch = result[0]

    assert (
        batch["batch_id"]
        == "batch-001"
    )

    assert (
        batch["status"]
        == "APPLIED"
    )

    assert (
        batch["budget_module"]
        == "OPEX"
    )

    assert batch["row_count"] == 3
    assert batch["field_count"] == 7

    assert len(
        client.calls
    ) == 1

    call = client.calls[0]

    assert (
        "ORDER BY"
        in call["sql"]
    )

    assert (
        "created_at DESC"
        in call["sql"]
    )

    assert (
        "COALESCE"
        in call["sql"]
    )

    params = parameter_map(
        call["job_config"]
    )

    assert (
        params["budget_module"]
        == "OPEX"
    )

    assert (
        params["status"]
        == "APPLIED"
    )

    assert params["limit"] == 25
    assert params["offset"] == 50

    assert (
        call["location"]
        == "US"
    )

    assert client.job.result_called


def test_list_batches_can_read_all_statuses():
    client = FakeClient(
        [
            make_history_row(
                status="CONFLICT"
            )
        ]
    )

    result = (
        repository(client)
        .list_batches(
            status=None
        )
    )

    assert len(result) == 1

    params = parameter_map(
        client.calls[0][
            "job_config"
        ]
    )

    assert params["status"] is None


def test_list_batches_uses_active_module():
    client = FakeClient(
        [
            make_history_row(
                batch_id="capex-001",
                module="CAPEX",
            )
        ]
    )

    result = (
        repository(
            client,
            module_config=(
                CAPEX_MODULE_CONFIG
            ),
        )
        .list_batches()
    )

    assert (
        result[0][
            "budget_module"
        ]
        == "CAPEX"
    )

    params = parameter_map(
        client.calls[0][
            "job_config"
        ]
    )

    assert (
        params["budget_module"]
        == "CAPEX"
    )


def test_unknown_batch_status_is_rejected():
    client = FakeClient()

    with pytest.raises(
        BigQueryPersistenceError,
        match="no reconocido",
    ):
        repository(
            client
        ).list_batches(
            status="OTRO"
        )

    assert client.calls == []


@pytest.mark.parametrize(
    (
        "limit",
        "offset",
    ),
    (
        (0, 0),
        (501, 0),
        (10, -1),
    ),
)
def test_invalid_pagination_is_rejected(
    limit,
    offset,
):
    client = FakeClient()

    with pytest.raises(
        BigQueryPersistenceError
    ):
        repository(
            client
        ).list_batches(
            limit=limit,
            offset=offset,
        )

    assert client.calls == []
