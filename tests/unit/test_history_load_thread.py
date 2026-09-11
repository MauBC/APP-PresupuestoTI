import pytest

from app.ui.workers.history_loader import (
    HistoryLoadThread,
)


pytestmark = pytest.mark.unit


class FakeHistoryService:
    def __init__(
        self,
        *,
        result=(),
        error=None,
    ):
        self.result = tuple(
            result
        )

        self.error = error
        self.calls = []

    def list_batches(
        self,
        *,
        status,
        limit,
        offset,
    ):
        self.calls.append(
            {
                "status": status,
                "limit": limit,
                "offset": offset,
            }
        )

        if self.error is not None:
            raise self.error

        return self.result


def test_history_worker_emits_loaded_batches():
    module_config = object()

    service = FakeHistoryService(
        result=(
            "batch-1",
            "batch-2",
        )
    )

    received = []
    failed = []

    worker = HistoryLoadThread(
        module_config,
        status="APPLIED",
        limit=25,
        offset=50,
        service_factory=(
            lambda config:
                service
        ),
    )

    worker.loaded.connect(
        received.append
    )

    worker.failed.connect(
        failed.append
    )

    worker.run()

    assert received == [
        (
            "batch-1",
            "batch-2",
        )
    ]

    assert failed == []

    assert service.calls == [
        {
            "status": "APPLIED",
            "limit": 25,
            "offset": 50,
        }
    ]


def test_history_worker_can_request_all_statuses():
    service = (
        FakeHistoryService()
    )

    worker = HistoryLoadThread(
        object(),
        status=None,
        service_factory=(
            lambda config:
                service
        ),
    )

    worker.run()

    assert (
        service.calls[0][
            "status"
        ]
        is None
    )


def test_history_worker_emits_failure():
    service = FakeHistoryService(
        error=RuntimeError(
            "network failure"
        )
    )

    received = []
    failed = []

    worker = HistoryLoadThread(
        object(),
        service_factory=(
            lambda config:
                service
        ),
    )

    worker.loaded.connect(
        received.append
    )

    worker.failed.connect(
        failed.append
    )

    worker.run()

    assert received == []

    assert len(failed) == 1

    assert (
        "RuntimeError"
        in failed[0]
    )

    assert (
        "network failure"
        in failed[0]
    )
