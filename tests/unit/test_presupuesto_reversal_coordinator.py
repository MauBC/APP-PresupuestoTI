from datetime import (
    datetime,
    timezone,
)
from types import SimpleNamespace

import pytest

from app.models.budget_history import (
    BudgetHistoryBatch,
)
from app.services.presupuesto_reversal_coordinator import (
    PresupuestoReversalCoordinator,
    PresupuestoReversalCoordinatorError,
)
from app.services.presupuesto_save_coordinator import (
    PresupuestoReloadAfterApplyError,
)
from database.persistence.models import (
    ConflictDetail,
    PersistenceResult,
)


pytestmark = pytest.mark.unit


FIXED_TIME = datetime(
    2026,
    9,
    8,
    22,
    0,
    tzinfo=timezone.utc,
)


def make_batch(
    *,
    module="OPEX",
):
    return BudgetHistoryBatch(
        batch_id="source-batch",
        status="APPLIED",
        actor="PC\\Mauro",
        created_at=FIXED_TIME,
        completed_at=FIXED_TIME,
        row_count=1,
        field_count=2,
        app_version="0.5.0",
        error_message=None,
        budget_module=module,
    )


class FakeWorkspace:
    def __init__(
        self,
        *,
        has_changes=False,
        module="OPEX",
    ):
        self.has_changes = (
            has_changes
        )

        self.module_config = (
            SimpleNamespace(
                module=(
                    SimpleNamespace(
                        value=module
                    )
                )
            )
        )


class FakeHistoryService:
    def __init__(
        self,
    ):
        self.calls = []

        self.detail = (
            SimpleNamespace(
                row_ids=(
                    "row-001",
                ),
                changes=(),
            )
        )

    def get_batch_detail(
        self,
        batch,
    ):
        self.calls.append(
            batch
        )

        return self.detail


class FakeReadRepository:
    def __init__(
        self,
    ):
        self.calls = []

        self.rows = (
            {
                "row_id": "row-001",
                "version": 2,
            },
        )

    def get_rows_by_ids(
        self,
        row_ids,
    ):
        self.calls.append(
            tuple(row_ids)
        )

        return self.rows


class FakeProposal:
    def __init__(
        self,
    ):
        self.batch = object()

        self.row_ids = (
            "row-001",
        )


class FakeReversalService:
    def __init__(
        self,
    ):
        self.calls = []

        self.proposal = (
            FakeProposal()
        )

    def build_proposal(
        self,
        detail,
        current_rows,
        **kwargs,
    ):
        self.calls.append(
            {
                "detail":
                    detail,
                "current_rows":
                    current_rows,
                **kwargs,
            }
        )

        return self.proposal


class FakePersistenceService:
    def __init__(
        self,
        result,
    ):
        self.result = result
        self.calls = []

    def persist_batch(
        self,
        batch,
    ):
        self.calls.append(
            batch
        )

        return self.result


class FakeLoader:
    def __init__(
        self,
        *,
        error=None,
    ):
        self.error = error
        self.calls = []

        self.result = (
            SimpleNamespace(
                row_count=1
            )
        )

    def reload_rows_by_ids(
        self,
        row_ids,
    ):
        self.calls.append(
            tuple(row_ids)
        )

        if self.error is not None:
            raise self.error

        return self.result


def applied_result():
    return PersistenceResult(
        batch_id="revert-batch",
        status="APPLIED",
        row_count=1,
        field_count=2,
    )


def make_coordinator(
    *,
    workspace=None,
    result=None,
    loader=None,
):
    workspace = (
        workspace
        or FakeWorkspace()
    )

    history = (
        FakeHistoryService()
    )

    reader = (
        FakeReadRepository()
    )

    reversal = (
        FakeReversalService()
    )

    persistence = (
        FakePersistenceService(
            result
            or applied_result()
        )
    )

    loader = (
        loader
        or FakeLoader()
    )

    coordinator = (
        PresupuestoReversalCoordinator(
            workspace=workspace,
            history_service=history,
            read_repository=reader,
            persistence_service=(
                persistence
            ),
            workspace_loader=loader,
            reversal_service=reversal,
            app_version="0.5.0",
        )
    )

    return (
        coordinator,
        history,
        reader,
        reversal,
        persistence,
        loader,
    )


def test_applied_reversal_runs_complete_flow():
    (
        coordinator,
        history,
        reader,
        reversal,
        persistence,
        loader,
    ) = make_coordinator()

    source = make_batch()

    factory = lambda: (
        "revert-batch"
    )

    outcome = (
        coordinator
        .revert_and_reload(
            source,
            actor="PC\\Reversor",
            timestamp=FIXED_TIME,
            batch_id_factory=factory,
        )
    )

    assert outcome.is_applied
    assert outcome.was_reloaded

    assert (
        outcome.source_batch
        is source
    )

    assert history.calls == [
        source
    ]

    assert reader.calls == [
        (
            "row-001",
        )
    ]

    assert len(
        reversal.calls
    ) == 1

    call = reversal.calls[0]

    assert (
        call["actor"]
        == "PC\\Reversor"
    )

    assert (
        call["app_version"]
        == "0.5.0"
    )

    assert (
        call["timestamp"]
        == FIXED_TIME
    )

    assert (
        call["batch_id_factory"]
        is factory
    )

    assert (
        call["expected_module"]
        == "OPEX"
    )

    assert persistence.calls == [
        reversal.proposal.batch
    ]

    assert loader.calls == [
        (
            "row-001",
        )
    ]


def test_conflict_does_not_reload():
    conflict = PersistenceResult(
        batch_id="revert-batch",
        status="CONFLICT",
        row_count=1,
        field_count=2,
        conflicts=(
            ConflictDetail(
                row_id="row-001",
                expected_version=2,
                current_version=3,
            ),
        ),
    )

    (
        coordinator,
        _,
        _,
        _,
        persistence,
        loader,
    ) = make_coordinator(
        result=conflict
    )

    outcome = (
        coordinator
        .revert_and_reload(
            make_batch(),
            actor="usuario",
        )
    )

    assert (
        outcome.status
        == "CONFLICT"
    )

    assert not outcome.was_reloaded

    assert len(
        persistence.calls
    ) == 1

    assert loader.calls == []


def test_failed_does_not_reload():
    failed = PersistenceResult(
        batch_id="revert-batch",
        status="FAILED",
        row_count=1,
        field_count=2,
        error_message=(
            "Synthetic failure"
        ),
    )

    (
        coordinator,
        _,
        _,
        _,
        _,
        loader,
    ) = make_coordinator(
        result=failed
    )

    outcome = (
        coordinator
        .revert_and_reload(
            make_batch(),
            actor="usuario",
        )
    )

    assert (
        outcome.status
        == "FAILED"
    )

    assert not outcome.was_reloaded
    assert loader.calls == []


def test_local_pending_changes_block_reversal():
    (
        coordinator,
        history,
        reader,
        reversal,
        persistence,
        loader,
    ) = make_coordinator(
        workspace=(
            FakeWorkspace(
                has_changes=True
            )
        )
    )

    with pytest.raises(
        PresupuestoReversalCoordinatorError,
        match="cambios locales",
    ):
        coordinator.revert_and_reload(
            make_batch(),
            actor="usuario",
        )

    assert history.calls == []
    assert reader.calls == []
    assert reversal.calls == []
    assert persistence.calls == []
    assert loader.calls == []


def test_module_mismatch_is_blocked():
    (
        coordinator,
        history,
        reader,
        reversal,
        persistence,
        loader,
    ) = make_coordinator(
        workspace=(
            FakeWorkspace(
                module="CAPEX"
            )
        )
    )

    with pytest.raises(
        PresupuestoReversalCoordinatorError,
        match="OPEX",
    ):
        coordinator.revert_and_reload(
            make_batch(
                module="OPEX"
            ),
            actor="usuario",
        )

    assert history.calls == []
    assert reader.calls == []
    assert reversal.calls == []
    assert persistence.calls == []
    assert loader.calls == []


def test_persistence_disabled_blocks_reversal():
    workspace = FakeWorkspace(
        module="CAPEX"
    )

    workspace.module_config.capabilities = (
        SimpleNamespace(
            persistence=False
        )
    )

    (
        coordinator,
        history,
        reader,
        reversal,
        persistence,
        loader,
    ) = make_coordinator(
        workspace=workspace
    )

    with pytest.raises(
        PresupuestoReversalCoordinatorError,
        match="persistencia",
    ):
        coordinator.revert_and_reload(
            make_batch(
                module="CAPEX"
            ),
            actor="usuario",
        )

    assert history.calls == []
    assert reader.calls == []
    assert reversal.calls == []
    assert persistence.calls == []
    assert loader.calls == []


def test_reload_failure_after_apply_is_explicit():
    loader = FakeLoader(
        error=RuntimeError(
            "reload failed"
        )
    )

    (
        coordinator,
        _,
        _,
        _,
        _,
        _,
    ) = make_coordinator(
        loader=loader
    )

    with pytest.raises(
        PresupuestoReloadAfterApplyError
    ) as exc_info:
        coordinator.revert_and_reload(
            make_batch(),
            actor="usuario",
        )

    assert (
        exc_info.value
        .persistence_result
        .is_applied
    )

    assert (
        exc_info.value
        .persistence_result
        .batch_id
        == "revert-batch"
    )

    assert loader.calls == [
        (
            "row-001",
        )
    ]


def test_wrong_batch_type_is_rejected():
    (
        coordinator,
        history,
        reader,
        reversal,
        persistence,
        loader,
    ) = make_coordinator()

    with pytest.raises(
        TypeError,
        match="BudgetHistoryBatch",
    ):
        coordinator.revert_and_reload(
            "source-batch",
            actor="usuario",
        )

    assert history.calls == []
    assert reader.calls == []
    assert reversal.calls == []
    assert persistence.calls == []
    assert loader.calls == []



def test_insert_batch_reversal_is_blocked():
    (
        coordinator,
        history,
        reader,
        reversal,
        persistence,
        loader,
    ) = make_coordinator()

    history.detail = (
        SimpleNamespace(
            row_ids=(
                "row-001",
            ),
            changes=(
                SimpleNamespace(
                    version_before=0,
                ),
            ),
        )
    )

    with pytest.raises(
        PresupuestoReversalCoordinatorError,
        match="altas nuevas",
    ):
        coordinator.revert_and_reload(
            make_batch(),
            actor="PC\\Reversor",
        )

    assert len(
        history.calls
    ) == 1

    assert reader.calls == []
    assert reversal.calls == []
    assert persistence.calls == []
    assert loader.calls == []
