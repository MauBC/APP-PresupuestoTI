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
    AuditBuildError,
    build_audit_changes,
    serialize_audit_value,
)
from database.persistence.batch_builder import (
    build_persistence_batch,
)


pytestmark = pytest.mark.unit


FIXED_TIME = datetime(
    2026,
    9,
    7,
    16,
    0,
    tzinfo=timezone.utc,
)


def make_row():
    row = {
        "row_id": "row-1",
        "version": 4,
        "habilitado": True,
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal(
            "0.00"
        )

    row[
        "enero_usd"
    ] = Decimal("100.00")

    row[
        "anio_usd"
    ] = Decimal("100.00")

    return row


def make_batch(
    workspace,
):
    return build_persistence_batch(
        workspace,
        actor="usuario@empresa.com",
        app_version="0.5.0",
        timestamp=FIXED_TIME,
        batch_id_factory=lambda: (
            "batch-001"
        ),
    )


def id_factory():
    counter = 0

    def generate():
        nonlocal counter

        counter += 1

        return (
            f"audit-{counter}"
        )

    return generate


def test_numeric_audit_rows_are_created():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row()
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("125.00"),
    )

    batch = make_batch(
        workspace
    )

    audit = build_audit_changes(
        batch,
        timestamp=FIXED_TIME,
        audit_id_factory=(
            id_factory()
        ),
    )

    assert len(audit) == 2

    by_column = {
        item.column_name: item
        for item in audit
    }

    january = by_column[
        "enero_usd"
    ]

    assert (
        january.before_value
        == "100.00"
    )

    assert (
        january.after_value
        == "125.00"
    )

    assert (
        january.value_type
        == "NUMERIC"
    )

    assert (
        january.version_before
        == 4
    )

    assert (
        january.version_after
        == 5
    )

    assert (
        january.row_id
        == "row-1"
    )

    assert (
        january.batch_id
        == "batch-001"
    )


def test_boolean_audit_is_lowercase():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row()
        ]
    )

    workspace.set_enabled(
        0,
        False,
    )

    batch = make_batch(
        workspace
    )

    audit = build_audit_changes(
        batch,
        timestamp=FIXED_TIME,
        audit_id_factory=(
            id_factory()
        ),
    )

    assert len(audit) == 1

    change = audit[0]

    assert (
        change.column_name
        == "habilitado"
    )

    assert (
        change.before_value
        == "true"
    )

    assert (
        change.after_value
        == "false"
    )

    assert (
        change.value_type
        == "BOOLEAN"
    )


def test_none_is_preserved_as_null():
    assert (
        serialize_audit_value(
            None,
            "NUMERIC",
        )
        is None
    )


def test_duplicate_audit_ids_are_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row()
        ]
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("125.00"),
    )

    batch = make_batch(
        workspace
    )

    with pytest.raises(
        AuditBuildError,
        match="duplicados",
    ):
        build_audit_changes(
            batch,
            timestamp=FIXED_TIME,
            audit_id_factory=lambda: (
                "same-id"
            ),
        )


def test_naive_audit_timestamp_is_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row()
        ]
    )

    workspace.set_enabled(
        0,
        False,
    )

    batch = make_batch(
        workspace
    )

    with pytest.raises(
        AuditBuildError,
        match="zona horaria",
    ):
        build_audit_changes(
            batch,
            timestamp=datetime(
                2026,
                9,
                7,
                16,
                0,
            ),
        )
