from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_persistence_service import (
    PresupuestoPersistenceService,
    PresupuestoPersistenceServiceError,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
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
    18,
    30,
    tzinfo=timezone.utc,
)


def make_row(
    *,
    row_id="row-001",
    version=1,
):
    row = {
        "row_id": row_id,
        "version": version,
        "habilitado": True,
        "pais": "PERU",
        "nombre_gasto": "Servicio A",
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal(
            "0.00"
        )

    row[
        "enero_usd"
    ] = Decimal(
        "100.00"
    )

    row[
        "anio_usd"
    ] = Decimal(
        "100.00"
    )

    return row


def make_workspace():
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


class FakePersistenceRepository:
    def __init__(
        self,
        *,
        result=None,
        insert_error=None,
        staging_error=None,
        apply_error=None,
        mark_failed_error=None,
    ):
        self.result = (
            result
            if result is not None
            else PersistenceResult(
                batch_id="batch-001",
                status="APPLIED",
                row_count=1,
                field_count=2,
            )
        )

        self.insert_error = (
            insert_error
        )

        self.staging_error = (
            staging_error
        )

        self.apply_error = (
            apply_error
        )

        self.mark_failed_error = (
            mark_failed_error
        )

        self.calls = []

    def insert_pending_batch(
        self,
        batch,
    ):
        self.calls.append(
            (
                "insert",
                batch,
            )
        )

        if (
            self.insert_error
            is not None
        ):
            raise self.insert_error

        return 1

    def stage_rows(
        self,
        rows,
    ):
        rows = tuple(
            rows
        )

        self.calls.append(
            (
                "staging",
                rows,
            )
        )

        if (
            self.staging_error
            is not None
        ):
            raise self.staging_error

        return len(
            rows
        )

    def apply_staged_batch(
        self,
        batch_id,
        actor,
    ):
        self.calls.append(
            (
                "apply",
                batch_id,
                actor,
            )
        )

        if (
            self.apply_error
            is not None
        ):
            raise self.apply_error

        return self.result

    def mark_batch_failed(
        self,
        batch_id,
        error_message,
    ):
        self.calls.append(
            (
                "failed",
                batch_id,
                error_message,
            )
        )

        if (
            self.mark_failed_error
            is not None
        ):
            raise (
                self.mark_failed_error
            )


def make_service(
    workspace,
    repository,
):
    return (
        PresupuestoPersistenceService(
            workspace,
            repository,
            app_version="0.5.0",
        )
    )


def save(
    service,
):
    return service.save_changes(
        actor="usuario@empresa.com",
        timestamp=FIXED_TIME,
        batch_id_factory=lambda: (
            "batch-001"
        ),
    )


def test_applied_executes_complete_flow():
    workspace = (
        make_workspace()
    )

    repository = (
        FakePersistenceRepository()
    )

    result = save(
        make_service(
            workspace,
            repository,
        )
    )

    assert result.status == "APPLIED"

    assert [
        call[0]
        for call in repository.calls
    ] == [
        "insert",
        "staging",
        "apply",
    ]

    inserted_batch = (
        repository.calls[0][1]
    )

    assert (
        inserted_batch.batch_id
        == "batch-001"
    )

    assert (
        inserted_batch.actor
        == "usuario@empresa.com"
    )

    assert (
        inserted_batch.row_count
        == 1
    )

    assert (
        inserted_batch.field_count
        == 2
    )


def test_applied_does_not_clear_workspace():
    workspace = (
        make_workspace()
    )

    repository = (
        FakePersistenceRepository()
    )

    result = save(
        make_service(
            workspace,
            repository,
        )
    )

    assert result.is_applied

    assert workspace.has_changes
    assert (
        workspace.pending_row_count
        == 1
    )

    assert (
        workspace.pending_change_count
        == 2
    )


def test_conflict_does_not_clear_workspace():
    workspace = (
        make_workspace()
    )

    repository = (
        FakePersistenceRepository(
            result=PersistenceResult(
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
        )
    )

    result = save(
        make_service(
            workspace,
            repository,
        )
    )

    assert (
        result.status
        == "CONFLICT"
    )

    assert result.has_conflicts
    assert workspace.has_changes

    assert (
        workspace.get_row(
            0
        )["enero_usd"]
        == Decimal(
            "125.00"
        )
    )


def test_failed_result_does_not_clear_workspace():
    workspace = (
        make_workspace()
    )

    repository = (
        FakePersistenceRepository(
            result=PersistenceResult(
                batch_id="batch-001",
                status="FAILED",
                row_count=1,
                field_count=2,
                error_message=(
                    "Synthetic failure"
                ),
            )
        )
    )

    result = save(
        make_service(
            workspace,
            repository,
        )
    )

    assert (
        result.status
        == "FAILED"
    )

    assert (
        result.error_message
        == "Synthetic failure"
    )

    assert workspace.has_changes


def test_no_changes_are_rejected_before_repository():
    workspace = (
        PresupuestoWorkspace()
    )

    workspace.load(
        [
            make_row()
        ]
    )

    repository = (
        FakePersistenceRepository()
    )

    service = make_service(
        workspace,
        repository,
    )

    with pytest.raises(
        PresupuestoPersistenceServiceError,
        match="No existen cambios pendientes",
    ):
        save(
            service
        )

    assert repository.calls == []


def test_insert_failure_stops_flow_and_preserves_workspace():
    workspace = (
        make_workspace()
    )

    repository = (
        FakePersistenceRepository(
            insert_error=RuntimeError(
                "insert failed"
            )
        )
    )

    with pytest.raises(
        PresupuestoPersistenceServiceError,
        match="registrar",
    ):
        save(
            make_service(
                workspace,
                repository,
            )
        )

    assert [
        call[0]
        for call in repository.calls
    ] == [
        "insert",
    ]

    assert workspace.has_changes


def test_staging_failure_marks_batch_failed():
    workspace = (
        make_workspace()
    )

    repository = (
        FakePersistenceRepository(
            staging_error=RuntimeError(
                "load failed"
            )
        )
    )

    with pytest.raises(
        PresupuestoPersistenceServiceError,
        match="staging",
    ):
        save(
            make_service(
                workspace,
                repository,
            )
        )

    assert [
        call[0]
        for call in repository.calls
    ] == [
        "insert",
        "staging",
        "failed",
    ]

    failed_call = (
        repository.calls[2]
    )

    assert (
        failed_call[1]
        == "batch-001"
    )

    assert (
        "load failed"
        in failed_call[2]
    )

    assert workspace.has_changes


def test_staging_failure_does_not_apply_transaction():
    workspace = (
        make_workspace()
    )

    repository = (
        FakePersistenceRepository(
            staging_error=RuntimeError(
                "load failed"
            )
        )
    )

    with pytest.raises(
        PresupuestoPersistenceServiceError
    ):
        save(
            make_service(
                workspace,
                repository,
            )
        )

    assert not any(
        call[0] == "apply"
        for call in repository.calls
    )


def test_apply_exception_keeps_workspace_and_does_not_force_failed():
    workspace = (
        make_workspace()
    )

    repository = (
        FakePersistenceRepository(
            apply_error=RuntimeError(
                "network uncertainty"
            )
        )
    )

    with pytest.raises(
        PresupuestoPersistenceServiceError,
        match="confirmar",
    ):
        save(
            make_service(
                workspace,
                repository,
            )
        )

    assert [
        call[0]
        for call in repository.calls
    ] == [
        "insert",
        "staging",
        "apply",
    ]

    assert not any(
        call[0] == "failed"
        for call in repository.calls
    )

    assert workspace.has_changes


def test_failed_marking_failure_is_reported():
    workspace = (
        make_workspace()
    )

    repository = (
        FakePersistenceRepository(
            staging_error=RuntimeError(
                "load failed"
            ),
            mark_failed_error=RuntimeError(
                "mark failed error"
            ),
        )
    )

    with pytest.raises(
        PresupuestoPersistenceServiceError,
        match="tampoco se pudo",
    ):
        save(
            make_service(
                workspace,
                repository,
            )
        )

    assert workspace.has_changes


def test_result_from_different_batch_is_rejected():
    workspace = (
        make_workspace()
    )

    repository = (
        FakePersistenceRepository(
            result=PersistenceResult(
                batch_id="another-batch",
                status="APPLIED",
                row_count=1,
                field_count=2,
            )
        )
    )

    with pytest.raises(
        PresupuestoPersistenceServiceError,
        match="batch distinto",
    ):
        save(
            make_service(
                workspace,
                repository,
            )
        )

    assert workspace.has_changes


