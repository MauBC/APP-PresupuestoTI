
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.models.budget_history import (
    BudgetAuditChange,
)
from app.services.new_budget_row_service import (
    NewBudgetRowService,
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
from database.persistence.contract import (
    INSERT_OPERATION,
    UPDATE_OPERATION,
)
from database.persistence.in_memory_repository import (
    InMemoryPersistenceRepository,
)
from database.persistence.staging_builder import (
    build_staging_rows,
)
from database.persistence.transaction_sql import (
    build_apply_staged_batch_sql,
)


pytestmark = pytest.mark.unit


NOW = datetime(
    2026,
    9,
    9,
    22,
    0,
    tzinfo=timezone.utc,
)


def make_existing():
    row = {
        "row_id": "existing-1",
        "version": 1,
        "habilitado": True,
        "pais": "PER",
    }

    for column in (
        OPEX_MODULE_CONFIG
        .amount_columns
    ):
        row[column] = (
            Decimal("0.00")
        )

    row["enero_usd"] = (
        Decimal("100.00")
    )

    row["anio_usd"] = (
        Decimal("100.00")
    )

    return row


def new_draft(
    *,
    row_id="new-1",
):
    return (
        NewBudgetRowService(
            OPEX_MODULE_CONFIG,
            row_id_factory=(
                lambda: row_id
            ),
        )
        .create_draft(
            {
                "pais": "PER",
                "nombre_gasto":
                    "Alta nueva",
                "moneda_facturacion":
                    "USD",
            },
            actor="tester",
            timestamp=NOW,
        )
    )


def build_batch(
    workspace,
):
    return (
        build_persistence_batch(
            workspace,
            actor="tester",
            app_version="test",
            timestamp=NOW,
            batch_id_factory=(
                lambda: "batch-m8c"
            ),
        )
    )


def test_new_draft_initializes_standby_amounts():
    draft = new_draft()

    assert (
        draft.row["enero_usd"]
        == Decimal("0.00")
    )

    assert (
        draft.row["enero_ml"]
        == Decimal("0.00")
    )

    assert (
        draft.row["enero_mf"]
        == Decimal("0.00")
    )


def test_capex_draft_initializes_ml_and_usd():
    draft = (
        NewBudgetRowService(
            CAPEX_MODULE_CONFIG,
            row_id_factory=(
                lambda: "capex-new"
            ),
        )
        .create_draft(
            {
                "anio": 2027,
                "cantidad": 1,
                "pais": "PER",
            },
            actor="tester",
            timestamp=NOW,
        )
    )

    assert (
        draft.row["enero_ml"]
        == Decimal("0.00")
    )

    assert (
        draft.row["enero_usd"]
        == Decimal("0.00")
    )


def test_workspace_add_new_row_is_pending():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        ()
    )

    session_id = (
        workspace.add_new_row(
            new_draft().row
        )
    )

    assert workspace.is_new_row(
        session_id
    )

    assert workspace.row_count == 1
    assert workspace.has_changes
    assert (
        workspace.pending_row_count
        == 1
    )


def test_undo_removes_new_row():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        ()
    )

    workspace.add_new_row(
        new_draft().row
    )

    assert workspace.undo_last()

    assert workspace.row_count == 0
    assert not workspace.has_changes


def test_discard_removes_new_rows():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        ()
    )

    workspace.add_new_row(
        new_draft().row
    )

    workspace.discard_all()

    assert workspace.row_count == 0
    assert not workspace.has_changes


def test_batch_builder_marks_new_row_insert():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        ()
    )

    session_id = (
        workspace.add_new_row(
            new_draft().row
        )
    )

    workspace.edit_month(
        session_id,
        "enero_usd",
        Decimal("250.00"),
    )

    batch = build_batch(
        workspace
    )

    assert batch.row_count == 1

    row = batch.rows[0]

    assert (
        row.operation
        == INSERT_OPERATION
    )

    assert row.is_insert

    assert (
        row.expected_version
        == 0
    )

    assert (
        row.version_after
        == 1
    )

    insert_values = (
        row.insert_dict()
    )

    assert (
        insert_values["pais"]
        == "PER"
    )

    assert (
        insert_values["enero_ml"]
        == Decimal("0.00")
    )

    assert (
        row.editable_dict()[
            "enero_usd"
        ]
        == Decimal("250.00")
    )


def test_staging_contains_insert_operation_and_payload():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        ()
    )

    workspace.add_new_row(
        new_draft().row
    )

    batch = build_batch(
        workspace
    )

    staging = (
        build_staging_rows(
            batch
        )[0]
    )

    assert staging.is_insert

    assert (
        staging.expected_version
        == 0
    )

    assert (
        staging.insert_payload
        is not None
    )

    assert (
        '"pais":"PER"'
        in staging.insert_payload
    )

    record = staging.as_record()

    assert (
        record["operation"]
        == "INSERT"
    )


def test_insert_audit_uses_zero_to_one():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        ()
    )

    workspace.add_new_row(
        new_draft().row
    )

    batch = build_batch(
        workspace
    )

    counter = 0

    def next_id():
        nonlocal counter
        counter += 1
        return f"audit-{counter}"

    audit = build_audit_changes(
        batch,
        timestamp=NOW,
        audit_id_factory=(
            next_id
        ),
    )

    assert len(audit) == (
        batch.field_count
    )

    assert all(
        change.version_before == 0
        for change in audit
    )

    assert all(
        change.version_after == 1
        for change in audit
    )

    by_column = {
        change.column_name:
            change
        for change in audit
    }

    assert (
        by_column["pais"]
        .value_type
        == "STRING"
    )

    assert (
        by_column["pais"]
        .before_value
        is None
    )

    assert (
        by_column["pais"]
        .after_value
        == "PER"
    )


def test_history_model_accepts_insert_version_pair():
    change = BudgetAuditChange(
        audit_id="audit",
        batch_id="batch",
        row_id="row",
        column_name="pais",
        value_type="STRING",
        before_value=None,
        after_value="PER",
        version_before=0,
        version_after=1,
        actor="tester",
        changed_at=NOW,
    )

    assert (
        change.version_before
        == 0
    )


def test_mixed_update_and_insert_are_applied_together():
    existing = make_existing()

    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        (
            existing,
        )
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("125.00"),
    )

    new_session = (
        workspace.add_new_row(
            new_draft().row
        )
    )

    workspace.edit_month(
        new_session,
        "enero_usd",
        Decimal("300.00"),
    )

    batch = build_batch(
        workspace
    )

    operations = {
        row.row_id:
            row.operation
        for row in batch.rows
    }

    assert operations == {
        "existing-1":
            UPDATE_OPERATION,
        "new-1":
            INSERT_OPERATION,
    }

    staging = build_staging_rows(
        batch
    )

    counter = 0

    def next_id():
        nonlocal counter
        counter += 1
        return f"audit-{counter}"

    audit = build_audit_changes(
        batch,
        timestamp=NOW,
        audit_id_factory=(
            next_id
        ),
    )

    repository = (
        InMemoryPersistenceRepository(
            (
                existing,
            )
        )
    )

    repository.create_batch(
        batch
    )

    repository.stage_rows(
        staging
    )

    result = (
        repository.apply_staged_batch(
            batch.batch_id,
            audit,
        )
    )

    assert result.is_applied

    stored_existing = (
        repository.get_row(
            "existing-1"
        )
    )

    assert (
        stored_existing["version"]
        == 2
    )

    assert (
        stored_existing[
            "enero_usd"
        ]
        == Decimal("125.00")
    )

    stored_new = (
        repository.get_row(
            "new-1"
        )
    )

    assert (
        stored_new["version"]
        == 1
    )

    assert (
        stored_new[
            "enero_usd"
        ]
        == Decimal("300.00")
    )

    assert (
        stored_new["pais"]
        == "PER"
    )


def test_insert_collision_aborts_entire_mixed_batch():
    existing = make_existing()

    collision = (
        new_draft(
            row_id="new-1"
        ).row
    )

    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        (
            existing,
        )
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("125.00"),
    )

    workspace.add_new_row(
        new_draft(
            row_id="new-1"
        ).row
    )

    batch = build_batch(
        workspace
    )

    staging = build_staging_rows(
        batch
    )

    database_collision = dict(
        collision
    )

    database_collision[
        "version"
    ] = 4

    repository = (
        InMemoryPersistenceRepository(
            (
                existing,
                database_collision,
            )
        )
    )

    repository.create_batch(
        batch
    )

    repository.stage_rows(
        staging
    )

    result = (
        repository.apply_staged_batch(
            batch.batch_id,
            (),
        )
    )

    assert (
        result.status
        == "CONFLICT"
    )

    assert (
        repository.get_row(
            "existing-1"
        )["enero_usd"]
        == Decimal("100.00")
    )

    assert (
        repository.get_row(
            "existing-1"
        )["version"]
        == 1
    )

    assert (
        repository.get_audit()
        == ()
    )


def test_transaction_sql_has_insert_branch():
    sql = (
        build_apply_staged_batch_sql(
            main_table_id=(
                "p.d.presupuesto"
            ),
            batch_table_id=(
                "p.d.batches"
            ),
            audit_table_id=(
                "p.d.audit"
            ),
            staging_table_id=(
                "p.d.staging"
            ),
            module_config=(
                OPEX_MODULE_CONFIG
            ),
        )
    )

    normalized = " ".join(
        sql.split()
    )

    assert (
        "WHEN NOT MATCHED"
        in sql
    )

    assert (
        "= 'INSERT'"
        in sql
    )

    assert (
        "expected_version != 0"
        in normalized
    )

    assert (
        "0 AS version_before"
        in sql
    )

    assert (
        "1 AS version_after"
        in sql
    )


def test_transaction_sql_insert_contract_is_module_aware():
    sql = (
        build_apply_staged_batch_sql(
            main_table_id="p.d.capex",
            batch_table_id="p.d.batch",
            audit_table_id="p.d.audit",
            staging_table_id="p.d.stage",
            module_config=(
                CAPEX_MODULE_CONFIG
            ),
        )
    )

    assert (
        "`cantidad`"
        in sql
    )

    assert (
        "`presupuestador`"
        in sql
    )

    assert (
        "$.presupuestador"
        in sql
    )

    assert (
        "$.cantidad"
        in sql
    )

    assert (
        "`enero_ml`"
        in sql
    )
