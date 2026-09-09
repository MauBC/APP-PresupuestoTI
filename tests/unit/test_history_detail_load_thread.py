import pytest

from app.ui.workers.history_detail_loader import (
    HistoryDetailLoadThread,
)


pytestmark = pytest.mark.unit


class FakeService:
    def __init__(
        self,
        *,
        detail=None,
        error=None,
    ):
        self.detail = detail
        self.error = error
        self.calls = []

    def get_batch_detail(
        self,
        batch,
    ):
        self.calls.append(
            batch
        )

        if self.error is not None:
            raise self.error

        return self.detail


def test_detail_worker_emits_loaded_detail():
    batch = object()
    detail = object()

    service = FakeService(
        detail=detail
    )

    received = []
    failed = []

    worker = (
        HistoryDetailLoadThread(
            object(),
            batch,
            service_factory=(
                lambda config:
                    service
            ),
        )
    )

    worker.loaded.connect(
        received.append
    )

    worker.failed.connect(
        failed.append
    )

    worker.run()

    assert received == [
        detail
    ]

    assert failed == []

    assert service.calls == [
        batch
    ]


def test_detail_worker_emits_failure():
    batch = object()

    service = FakeService(
        error=RuntimeError(
            "detail failed"
        )
    )

    received = []
    failed = []

    worker = (
        HistoryDetailLoadThread(
            object(),
            batch,
            service_factory=(
                lambda config:
                    service
            ),
        )
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
        "detail failed"
        in failed[0]
    )


def test_detail_worker_uses_selected_batch():
    first = object()
    second = object()

    service = FakeService(
        detail="detail"
    )

    worker = (
        HistoryDetailLoadThread(
            object(),
            second,
            service_factory=(
                lambda config:
                    service
            ),
        )
    )

    worker.run()

    assert service.calls == [
        second
    ]

    assert first is not second
