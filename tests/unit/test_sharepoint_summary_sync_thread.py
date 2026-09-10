
from types import SimpleNamespace

import pytest

from app.ui.workers.sharepoint_summary_sync import (
    CapexSharePointSummarySyncThread,
    SharePointSummarySyncThreadFailure,
)


pytestmark = pytest.mark.unit


class FakeService:
    def __init__(
        self,
        *,
        error=None,
    ):
        self.error = error
        self.calls = []

    def prepare(
        self,
    ):
        self.calls.append(
            (
                "prepare",
                None,
            )
        )

        if self.error:
            raise self.error

        return "preparation"

    def publish(
        self,
        preparation,
        *,
        source_batch_id=None,
    ):
        self.calls.append(
            (
                "publish",
                source_batch_id,
            )
        )

        if self.error:
            raise self.error

        return SimpleNamespace(
            publish_result=(
                SimpleNamespace(
                    created_count=0,
                    updated_count=1,
                    deleted_count=0,
                    write_count=1,
                    sync_run_id="sync-1",
                )
            )
        )


def test_worker_completes():
    service = FakeService()

    worker = (
        CapexSharePointSummarySyncThread(
            source_batch_id="batch-1",
            service_factory=(
                lambda:
                    service
            ),
        )
    )

    completed = []
    failed = []

    worker.completed.connect(
        completed.append
    )

    worker.failed.connect(
        failed.append
    )

    worker.run()

    assert len(completed) == 1
    assert failed == []

    assert service.calls == [
        (
            "prepare",
            None,
        ),
        (
            "publish",
            "batch-1",
        ),
    ]


def test_worker_allows_manual_sync_without_batch():
    service = FakeService()

    worker = (
        CapexSharePointSummarySyncThread(
            service_factory=(
                lambda:
                    service
            ),
        )
    )

    worker.run()

    assert service.calls[-1] == (
        "publish",
        None,
    )


def test_worker_failure_is_separate_from_bigquery():
    service = FakeService(
        error=RuntimeError(
            "Synthetic SharePoint failure"
        )
    )

    worker = (
        CapexSharePointSummarySyncThread(
            source_batch_id="batch-1",
            service_factory=(
                lambda:
                    service
            ),
        )
    )

    completed = []
    failed = []

    worker.completed.connect(
        completed.append
    )

    worker.failed.connect(
        failed.append
    )

    worker.run()

    assert completed == []
    assert len(failed) == 1

    failure = failed[0]

    assert isinstance(
        failure,
        SharePointSummarySyncThreadFailure,
    )

    assert (
        failure.source_batch_id
        == "batch-1"
    )

    assert (
        "Synthetic SharePoint failure"
        in failure.message
    )
