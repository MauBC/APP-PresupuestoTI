from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from database.persistence.audit_builder import (
    build_audit_changes,
)
from database.persistence.batch_builder import (
    build_persistence_batch,
)
from database.persistence.in_memory_repository import (
    InMemoryPersistenceRepository,
)
from database.persistence.staging_builder import (
    build_staging_rows,
)


pytestmark = pytest.mark.unit


FIXED_TIME = datetime(
    2026,
    9,
    7,
    17,
    0,
    tzinfo=timezone.utc,
)


def make_row(
    *,
    row_id,
    version=1,
    amount="100.00",
):
    row = {
        "row_id": row_id,
        "version": version,
        "habilitado": True,
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal(
            "0.00"
        )

    row[
        "enero_usd"
    ] = Decimal(amount)

    row[
        "anio_usd"
    ] = Decimal(amount)

    return row


def prepare(
    workspace,
):
    batch = build_persistence_batch(
        workspace,
        actor="usuario@empresa.com",
        app_version="0.5.0",
        timestamp=FIXED_TIME,
        batch_id_factory=lambda: (
            "batch-001"
        ),
    )

    staging = build_staging_rows(
        batch,
        timestamp=FIXED_TIME,
    )

    counter = 0

    def audit_id():
        nonlocal counter

        counter += 1

        return f"audit-{counter}"

    audit = build_audit_changes(
        batch,
        timestamp=FIXED_TIME,
        audit_id_factory=audit_id,
    )

    return (
        batch,
        staging,
        audit,
    )


def test_success_updates_values_and_version():
    source = make_row(
        row_id="row-1",
        version=3,
    )

    workspace = (
        PresupuestoWorkspace()
    )

    workspace.load(
        [source]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("150.00"),
    )

    (
        batch,
        staging,
        audit,
    ) = prepare(
        workspace
    )

    repository = (
        InMemoryPersistenceRepository(
            [source]
        )
    )

    repository.create_batch(
        batch
    )

    repository.stage_rows(
        staging
    )

    result = (
        repository
        .apply_staged_batch(
            batch.batch_id,
            audit,
        )
    )

    assert result.is_applied
    assert result.status == (
        "APPLIED"
    )

    stored = repository.get_row(
        "row-1"
    )

    assert (
        stored["version"]
        == 4
    )

    assert (
        stored["enero_usd"]
        == Decimal("150.00")
    )

    assert (
        stored["anio_usd"]
        == Decimal("150.00")
    )

    assert (
        len(
            repository.get_audit()
        )
        == 2
    )

    assert not repository.has_staging(
        "batch-001"
    )

    assert (
        repository
        .get_batch(
            "batch-001"
        )
        .status
        == "APPLIED"
    )


def test_disable_is_persisted_without_deleting_row():
    source = make_row(
        row_id="row-1",
    )

    workspace = (
        PresupuestoWorkspace()
    )

    workspace.load(
        [source]
    )

    workspace.set_enabled(
        0,
        False,
    )

    (
        batch,
        staging,
        audit,
    ) = prepare(
        workspace
    )

    repository = (
        InMemoryPersistenceRepository(
            [source]
        )
    )

    repository.create_batch(
        batch
    )

    repository.stage_rows(
        staging
    )

    repository.apply_staged_batch(
        batch.batch_id,
        audit,
    )

    stored = repository.get_row(
        "row-1"
    )

    assert (
        stored["habilitado"]
        is False
    )

    assert (
        stored["version"]
        == 2
    )

    assert (
        stored["enero_usd"]
        == Decimal("100.00")
    )


def test_version_conflict_aborts_update():
    workspace_source = make_row(
        row_id="row-1",
        version=3,
    )

    database_source = make_row(
        row_id="row-1",
        version=4,
        amount="999.00",
    )

    workspace = (
        PresupuestoWorkspace()
    )

    workspace.load(
        [
            workspace_source
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("150.00"),
    )

    (
        batch,
        staging,
        audit,
    ) = prepare(
        workspace
    )

    repository = (
        InMemoryPersistenceRepository(
            [
                database_source
            ]
        )
    )

    repository.create_batch(
        batch
    )

    repository.stage_rows(
        staging
    )

    result = (
        repository
        .apply_staged_batch(
            batch.batch_id,
            audit,
        )
    )

    assert (
        result.status
        == "CONFLICT"
    )

    assert result.has_conflicts
    assert len(
        result.conflicts
    ) == 1

    conflict = (
        result.conflicts[0]
    )

    assert (
        conflict.row_id
        == "row-1"
    )

    assert (
        conflict.expected_version
        == 3
    )

    assert (
        conflict.current_version
        == 4
    )

    stored = repository.get_row(
        "row-1"
    )

    assert (
        stored["version"]
        == 4
    )

    assert (
        stored["enero_usd"]
        == Decimal("999.00")
    )

    assert (
        repository.get_audit()
        == ()
    )

    assert not repository.has_staging(
        "batch-001"
    )

    assert (
        repository
        .get_batch(
            "batch-001"
        )
        .status
        == "CONFLICT"
    )


def test_one_conflict_aborts_entire_batch():
    workspace_row_a = make_row(
        row_id="row-a",
        version=1,
    )

    workspace_row_b = make_row(
        row_id="row-b",
        version=1,
    )

    database_row_a = make_row(
        row_id="row-a",
        version=1,
    )

    database_row_b = make_row(
        row_id="row-b",
        version=2,
        amount="500.00",
    )

    workspace = (
        PresupuestoWorkspace()
    )

    workspace.load(
        [
            workspace_row_a,
            workspace_row_b,
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("150.00"),
    )

    workspace.edit_month(
        1,
        "enero_usd",
        Decimal("200.00"),
    )

    (
        batch,
        staging,
        audit,
    ) = prepare(
        workspace
    )

    repository = (
        InMemoryPersistenceRepository(
            [
                database_row_a,
                database_row_b,
            ]
        )
    )

    repository.create_batch(
        batch
    )

    repository.stage_rows(
        staging
    )

    result = (
        repository
        .apply_staged_batch(
            batch.batch_id,
            audit,
        )
    )

    assert (
        result.status
        == "CONFLICT"
    )

    row_a = repository.get_row(
        "row-a"
    )

    row_b = repository.get_row(
        "row-b"
    )

    assert (
        row_a["enero_usd"]
        == Decimal("100.00")
    )

    assert (
        row_a["version"]
        == 1
    )

    assert (
        row_b["enero_usd"]
        == Decimal("500.00")
    )

    assert (
        row_b["version"]
        == 2
    )

    assert (
        repository.get_audit()
        == ()
    )


def test_missing_database_row_is_conflict():
    workspace_source = make_row(
        row_id="missing-row",
        version=1,
    )

    workspace = (
        PresupuestoWorkspace()
    )

    workspace.load(
        [
            workspace_source
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("150.00"),
    )

    (
        batch,
        staging,
        audit,
    ) = prepare(
        workspace
    )

    repository = (
        InMemoryPersistenceRepository()
    )

    repository.create_batch(
        batch
    )

    repository.stage_rows(
        staging
    )

    result = (
        repository
        .apply_staged_batch(
            batch.batch_id,
            audit,
        )
    )

    assert (
        result.status
        == "CONFLICT"
    )

    assert (
        result.conflicts[0]
        .current_version
        is None
    )


def test_multiple_rows_are_applied_together():
    row_a = make_row(
        row_id="row-a",
    )

    row_b = make_row(
        row_id="row-b",
    )

    workspace = (
        PresupuestoWorkspace()
    )

    workspace.load(
        [
            row_a,
            row_b,
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("120.00"),
    )

    workspace.edit_month(
        1,
        "enero_usd",
        Decimal("130.00"),
    )

    (
        batch,
        staging,
        audit,
    ) = prepare(
        workspace
    )

    repository = (
        InMemoryPersistenceRepository(
            [
                row_a,
                row_b,
            ]
        )
    )

    repository.create_batch(
        batch
    )

    repository.stage_rows(
        staging
    )

    result = (
        repository
        .apply_staged_batch(
            batch.batch_id,
            audit,
        )
    )

    assert (
        result.status
        == "APPLIED"
    )

    assert result.row_count == 2
    assert result.field_count == 4

    assert (
        repository
        .get_row(
            "row-a"
        )["version"]
        == 2
    )

    assert (
        repository
        .get_row(
            "row-b"
        )["version"]
        == 2
    )
