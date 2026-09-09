from types import SimpleNamespace

import pytest

from app.services.presupuesto_save_coordinator import (
    PresupuestoReloadAfterApplyError,
)
from app.ui.workers.presupuesto_reversal import (
    PresupuestoReversalThread,
    PresupuestoReversalThreadFailure,
)
from database.persistence.models import (
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

    def revert_and_reload(
        self,
        batch,
        *,
        actor,
    ):
        self.calls.append(
            {
                "batch": batch,
                "actor": actor,
            }
        )

        if self.error is not None:
            raise self.error

        return self.outcome


def make_batch():
    return SimpleNamespace(
        batch_id="source-batch-001"
    )


def test_reversal_worker_emits_completed():
    batch = make_batch()

    outcome = SimpleNamespace(
        status="APPLIED"
    )

    coordinator = FakeCoordinator(
        outcome=outcome
    )

    received = []
    failed = []

    worker = PresupuestoReversalThread(
        DummyWorkspace(),
        batch,
        "PC\\Mauro",
        coordinator_factory=(
            lambda workspace:
                coordinator
        ),
    )

    worker.completed.connect(
        received.append
    )

    worker.failed.connect(
        failed.append
    )

    worker.run()

    assert received == [
        outcome
    ]

    assert failed == []

    assert coordinator.calls == [
        {
            "batch": batch,
            "actor": "PC\\Mauro",
        }
    ]


def test_reversal_conflict_is_completed():
    outcome = SimpleNamespace(
        status="CONFLICT"
    )

    coordinator = FakeCoordinator(
        outcome=outcome
    )

    completed = []

    worker = PresupuestoReversalThread(
        DummyWorkspace(),
        make_batch(),
        "usuario",
        coordinator_factory=(
            lambda workspace:
                coordinator
        ),
    )

    worker.completed.connect(
        completed.append
    )

    worker.run()

    assert completed == [
        outcome
    ]


def test_regular_failure_reports_not_applied():
    coordinator = FakeCoordinator(
        error=RuntimeError(
            "network failure"
        )
    )

    failures = []

    worker = PresupuestoReversalThread(
        DummyWorkspace(),
        make_batch(),
        "usuario",
        coordinator_factory=(
            lambda workspace:
                coordinator
        ),
    )

    worker.failed.connect(
        failures.append
    )

    worker.run()

    assert len(failures) == 1

    failure = failures[0]

    assert isinstance(
        failure,
        PresupuestoReversalThreadFailure,
    )

    assert not failure.was_applied

    assert (
        failure.source_batch_id
        == "source-batch-001"
    )

    assert failure.batch_id is None

    assert (
        "network failure"
        in failure.message
    )


def test_reload_failure_reports_applied():
    result = PersistenceResult(
        batch_id="revert-batch-001",
        status="APPLIED",
        row_count=1,
        field_count=2,
    )

    coordinator = FakeCoordinator(
        error=(
            PresupuestoReloadAfterApplyError(
                result
            )
        )
    )

    failures = []

    worker = PresupuestoReversalThread(
        DummyWorkspace(),
        make_batch(),
        "usuario",
        coordinator_factory=(
            lambda workspace:
                coordinator
        ),
    )

    worker.failed.connect(
        failures.append
    )

    worker.run()

    assert len(failures) == 1

    failure = failures[0]

    assert failure.was_applied

    assert (
        failure.batch_id
        == "revert-batch-001"
    )

    assert (
        failure.source_batch_id
        == "source-batch-001"
    )


def test_empty_actor_is_rejected():
    with pytest.raises(
        ValueError,
        match="actor",
    ):
        PresupuestoReversalThread(
            DummyWorkspace(),
            make_batch(),
            "   ",
        )


def test_missing_batch_id_is_rejected():
    with pytest.raises(
        ValueError,
        match="batch_id",
    ):
        PresupuestoReversalThread(
            DummyWorkspace(),
            SimpleNamespace(
                batch_id=""
            ),
            "usuario",
        )
