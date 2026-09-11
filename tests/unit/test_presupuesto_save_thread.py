import pytest

from app.services.presupuesto_save_coordinator import (
    PresupuestoReloadAfterApplyError,
    PresupuestoSaveOutcome,
)
from app.ui.workers.presupuesto_save import (
    PresupuestoSaveThread,
    PresupuestoSaveThreadFailure,
)
from database.persistence.models import (
    ConflictDetail,
    PersistenceResult,
)


pytestmark = pytest.mark.unit


class DummyWorkspace:
    pass


class FakeCoordinator:
    def __init__(
        self,
        *,
        outcome=None,
        error=None,
    ):
        self.outcome = outcome
        self.error = error
        self.calls = []

    def save_and_reload(
        self,
        **kwargs,
    ):
        self.calls.append(
            kwargs
        )

        if self.error is not None:
            raise self.error

        return self.outcome


def applied_outcome():
    result = PersistenceResult(
        batch_id="batch-001",
        status="APPLIED",
        row_count=1,
        field_count=2,
    )

    return PresupuestoSaveOutcome(
        persistence_result=result,
        reload_result=None,
    )


def conflict_outcome():
    result = PersistenceResult(
        batch_id="batch-002",
        status="CONFLICT",
        row_count=1,
        field_count=2,
        conflicts=(
            ConflictDetail(
                row_id="row-001",
                expected_version=1,
                current_version=2,
            ),
        ),
    )

    return PresupuestoSaveOutcome(
        persistence_result=result,
        reload_result=None,
    )


def test_completed_signal_emits_outcome():
    workspace = DummyWorkspace()

    coordinator = (
        FakeCoordinator(
            outcome=applied_outcome()
        )
    )

    factory_calls = []

    def factory(
        received_workspace,
    ):
        factory_calls.append(
            received_workspace
        )

        return coordinator

    worker = PresupuestoSaveThread(
        workspace,
        "usuario@empresa.com",
        coordinator_factory=factory,
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

    assert (
        completed[0].status
        == "APPLIED"
    )

    assert factory_calls == [
        workspace
    ]

    assert coordinator.calls == [
        {
            "actor":
                "usuario@empresa.com"
        }
    ]


def test_conflict_is_completed_not_worker_failure():
    coordinator = (
        FakeCoordinator(
            outcome=(
                conflict_outcome()
            )
        )
    )

    worker = PresupuestoSaveThread(
        DummyWorkspace(),
        "usuario@empresa.com",
        coordinator_factory=(
            lambda workspace:
                coordinator
        ),
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

    assert (
        completed[0].status
        == "CONFLICT"
    )


def test_regular_error_reports_not_applied():
    coordinator = (
        FakeCoordinator(
            error=RuntimeError(
                "network failure"
            )
        )
    )

    worker = PresupuestoSaveThread(
        DummyWorkspace(),
        "usuario@empresa.com",
        coordinator_factory=(
            lambda workspace:
                coordinator
        ),
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
        PresupuestoSaveThreadFailure,
    )

    assert (
        failure.message
        == "network failure"
    )

    assert (
        failure.was_applied
        is False
    )

    assert failure.batch_id is None


def test_reload_error_reports_applied_batch():
    result = PersistenceResult(
        batch_id="batch-applied-001",
        status="APPLIED",
        row_count=1,
        field_count=2,
    )

    coordinator = (
        FakeCoordinator(
            error=(
                PresupuestoReloadAfterApplyError(
                    result
                )
            )
        )
    )

    worker = PresupuestoSaveThread(
        DummyWorkspace(),
        "usuario@empresa.com",
        coordinator_factory=(
            lambda workspace:
                coordinator
        ),
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

    assert failure.was_applied
    assert (
        failure.batch_id
        == "batch-applied-001"
    )

    assert (
        "aplicados correctamente"
        in failure.message
    )


def test_empty_actor_is_rejected():
    with pytest.raises(
        ValueError,
        match="actor",
    ):
        PresupuestoSaveThread(
            DummyWorkspace(),
            "   ",
        )
