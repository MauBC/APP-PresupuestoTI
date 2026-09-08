from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_save_coordinator import (
    PresupuestoReloadAfterApplyError,
    PresupuestoSaveCoordinator,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_loader import (
    PresupuestoWorkspaceLoader,
    WorkspaceLoadResult,
)
from database.persistence.models import (
    ConflictDetail,
    PersistenceResult,
)


pytestmark = pytest.mark.unit


FIXED_TIME = datetime(
    2026,
    9,
    7,
    19,
    0,
    tzinfo=timezone.utc,
)


def make_row(
    *,
    amount="100.00",
    version=1,
):
    row = {
        "row_id": "row-001",
        "version": version,
        "habilitado": True,
        "pais": "PERU",
        "nombre_gasto": "Servicio A",
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal(
            "0.00"
        )

    row["enero_usd"] = Decimal(
        amount
    )

    row["anio_usd"] = Decimal(
        amount
    )

    return row


def make_dirty_workspace():
    workspace = (
        PresupuestoWorkspace()
    )

    workspace.load(
        [
            make_row()
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal(
            "125.00"
        ),
    )

    return workspace


class FakePersistenceService:
    def __init__(
        self,
        *,
        result=None,
        error=None,
    ):
        self.result = result
        self.error = error
        self.calls = []

    def save_changes(
        self,
        **kwargs,
    ):
        self.calls.append(
            kwargs
        )

        if self.error is not None:
            raise self.error

        return self.result


class FakeLoader:
    def __init__(
        self,
        *,
        result=None,
        error=None,
    ):
        self.result = (
            result
            if result is not None
            else WorkspaceLoadResult(
                row_count=1,
                fetch_seconds=0.01,
                workspace_seconds=0.01,
                total_seconds=0.02,
            )
        )

        self.error = error
        self.calls = 0

    def load(self):
        self.calls += 1

        if self.error is not None:
            raise self.error

        return self.result


class FakeRepository:
    def __init__(
        self,
        rows,
    ):
        self.rows = tuple(
            rows
        )

        self.calls = 0

    def get_all_rows(self):
        self.calls += 1
        return self.rows

    def get_rows_by_ids(
        self,
        row_ids,
    ):
        wanted = {
            str(row_id).strip()
            for row_id in row_ids
        }

        return tuple(
            row
            for row in self.get_all_rows()
            if str(
                row.get(
                    "row_id",
                    ""
                )
            ).strip()
            in wanted
        )



def applied_result():
    return PersistenceResult(
        batch_id="batch-001",
        status="APPLIED",
        row_count=1,
        field_count=2,
    )


def test_applied_triggers_reload():
    persistence = (
        FakePersistenceService(
            result=applied_result()
        )
    )

    loader = FakeLoader()

    coordinator = (
        PresupuestoSaveCoordinator(
            persistence,
            loader,
        )
    )

    outcome = (
        coordinator.save_and_reload(
            actor="usuario@empresa.com",
            timestamp=FIXED_TIME,
            batch_id_factory=lambda: (
                "batch-001"
            ),
        )
    )

    assert outcome.status == "APPLIED"
    assert outcome.is_applied
    assert outcome.was_reloaded

    assert loader.calls == 1

    assert (
        outcome.reload_result.row_count
        == 1
    )


def test_applied_real_loader_cleans_workspace():
    workspace = (
        make_dirty_workspace()
    )

    assert workspace.has_changes
    assert (
        workspace.pending_change_count
        == 2
    )

    repository = (
        FakeRepository(
            [
                make_row(
                    amount="125.00",
                    version=2,
                )
            ]
        )
    )

    loader = (
        PresupuestoWorkspaceLoader(
            repository,
            workspace,
        )
    )

    persistence = (
        FakePersistenceService(
            result=applied_result()
        )
    )

    coordinator = (
        PresupuestoSaveCoordinator(
            persistence,
            loader,
        )
    )

    outcome = (
        coordinator.save_and_reload(
            actor="usuario@empresa.com",
            timestamp=FIXED_TIME,
            batch_id_factory=lambda: (
                "batch-001"
            ),
        )
    )

    assert outcome.is_applied
    assert outcome.was_reloaded

    assert repository.calls == 1

    assert not workspace.has_changes
    assert (
        workspace.pending_row_count
        == 0
    )

    assert (
        workspace.pending_change_count
        == 0
    )

    assert (
        workspace.history_count
        == 0
    )

    row = workspace.get_row(
        0
    )

    assert row["version"] == 2

    assert (
        row["enero_usd"]
        == Decimal(
            "125.00"
        )
    )

    assert (
        row["anio_usd"]
        == Decimal(
            "125.00"
        )
    )


def test_conflict_does_not_reload():
    conflict = PersistenceResult(
        batch_id="batch-001",
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

    persistence = (
        FakePersistenceService(
            result=conflict
        )
    )

    loader = FakeLoader()

    outcome = (
        PresupuestoSaveCoordinator(
            persistence,
            loader,
        )
        .save_and_reload(
            actor="usuario@empresa.com",
        )
    )

    assert (
        outcome.status
        == "CONFLICT"
    )

    assert not outcome.was_reloaded

    assert loader.calls == 0


def test_failed_does_not_reload():
    failed = PersistenceResult(
        batch_id="batch-001",
        status="FAILED",
        row_count=1,
        field_count=2,
        error_message=(
            "Synthetic failure"
        ),
    )

    persistence = (
        FakePersistenceService(
            result=failed
        )
    )

    loader = FakeLoader()

    outcome = (
        PresupuestoSaveCoordinator(
            persistence,
            loader,
        )
        .save_and_reload(
            actor="usuario@empresa.com",
        )
    )

    assert outcome.status == "FAILED"

    assert not outcome.was_reloaded

    assert loader.calls == 0


def test_reload_error_after_applied_is_explicit():
    result = applied_result()

    persistence = (
        FakePersistenceService(
            result=result
        )
    )

    loader = FakeLoader(
        error=RuntimeError(
            "reload failed"
        )
    )

    coordinator = (
        PresupuestoSaveCoordinator(
            persistence,
            loader,
        )
    )

    with pytest.raises(
        PresupuestoReloadAfterApplyError
    ) as exc_info:
        coordinator.save_and_reload(
            actor="usuario@empresa.com",
        )

    assert (
        exc_info.value
        .persistence_result
        is result
    )

    assert (
        exc_info.value
        .persistence_result
        .is_applied
    )

    assert loader.calls == 1


def test_save_arguments_are_forwarded():
    persistence = (
        FakePersistenceService(
            result=PersistenceResult(
                batch_id="batch-001",
                status="CONFLICT",
                row_count=1,
                field_count=1,
                conflicts=(
                    ConflictDetail(
                        row_id="row-001",
                        expected_version=1,
                        current_version=2,
                    ),
                ),
            )
        )
    )

    loader = FakeLoader()

    factory = lambda: "batch-001"

    coordinator = (
        PresupuestoSaveCoordinator(
            persistence,
            loader,
        )
    )

    coordinator.save_and_reload(
        actor="usuario@empresa.com",
        timestamp=FIXED_TIME,
        batch_id_factory=factory,
    )

    assert len(
        persistence.calls
    ) == 1

    call = persistence.calls[0]

    assert (
        call["actor"]
        == "usuario@empresa.com"
    )

    assert (
        call["timestamp"]
        == FIXED_TIME
    )

    assert (
        call["batch_id_factory"]
        is factory
    )


