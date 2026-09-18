
from types import SimpleNamespace

import pytest

from app.services.sharepoint_summary_publisher import (
    SharePointLargeDeleteGuardError,
)
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
        allow_large_delete=False,
    ):
        self.calls.append(
            (
                "publish",
                source_batch_id,
                allow_large_delete,
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
            False,
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
        False,
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

def test_worker_passes_large_delete_authorization():
    service = FakeService()

    worker = CapexSharePointSummarySyncThread(
        source_batch_id="batch-large",
        allow_large_delete=True,
        service_factory=(
            lambda: service
        ),
    )

    worker.run()

    assert service.calls[-1] == (
        "publish",
        "batch-large",
        True,
    )


def test_worker_exposes_large_delete_plan():
    class GuardService:
        def prepare(self):
            return SimpleNamespace(
                plan=SimpleNamespace(
                    create_count=81,
                    update_count=14,
                    delete_count=141,
                    unchanged_count=2,
                    unmanaged_count=0,
                    current_item_count=157,
                    desired_item_count=97,
                )
            )

        def publish(
            self,
            preparation,
            *,
            source_batch_id=None,
            allow_large_delete=False,
        ):
            raise SharePointLargeDeleteGuardError(
                "Se bloqueo una eliminacion masiva."
            )

    worker = CapexSharePointSummarySyncThread(
        source_batch_id="batch-cutover",
        service_factory=GuardService,
    )

    failures = []

    worker.failed.connect(
        failures.append
    )

    worker.run()

    assert len(failures) == 1

    failure = failures[0]

    assert (
        failure
        .requires_large_delete_confirmation
    )

    assert failure.create_count == 81
    assert failure.update_count == 14
    assert failure.delete_count == 141
    assert failure.current_item_count == 157
    assert failure.desired_item_count == 97
