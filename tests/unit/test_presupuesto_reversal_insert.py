from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
    USD_MONTH_COLUMNS,
)
from app.models.budget_history import (
    BudgetAuditChange,
    BudgetHistoryBatch,
    BudgetHistoryDetail,
)
from app.services.presupuesto_reversal_service import (
    PresupuestoReversalConflictError,
    PresupuestoReversalError,
    PresupuestoReversalService,
)


pytestmark = pytest.mark.unit


NOW = datetime(
    2026,
    9,
    10,
    22,
    0,
    tzinfo=timezone.utc,
)


def make_audit(
    column,
    before,
    after,
    *,
    row_id="row-1",
    value_type="NUMERIC",
    version_before=0,
    version_after=1,
):
    return BudgetAuditChange(
        audit_id=(
            f"audit-{row_id}-{column}"
        ),
        batch_id="source-batch",
        row_id=row_id,
        column_name=column,
        value_type=value_type,
        before_value=before,
        after_value=after,
        version_before=version_before,
        version_after=version_after,
        actor="PC\\Mauro",
        changed_at=NOW,
    )


def make_detail(
    changes,
    *,
    module="OPEX",
):
    changes = tuple(
        changes
    )

    row_ids = tuple(
        dict.fromkeys(
            change.row_id
            for change in changes
        )
    )

    batch = BudgetHistoryBatch(
        batch_id="source-batch",
        status="APPLIED",
        actor="PC\\Mauro",
        created_at=NOW,
        completed_at=NOW,
        row_count=len(
            row_ids
        ),
        field_count=len(
            changes
        ),
        app_version="0.5.0",
        error_message=None,
        budget_module=module,
    )

    return BudgetHistoryDetail(
        batch=batch,
        changes=changes,
    )


def current_row(
    *,
    row_id="row-1",
    version=1,
    january="100.00",
    enabled=True,
):
    row = {
        "row_id": row_id,
        "version": version,
        HABILITADO_COLUMN:
            enabled,
    }

    for column in (
        USD_MONTH_COLUMNS
    ):
        row[column] = Decimal(
            "0.00"
        )

    row["enero_usd"] = Decimal(
        january
    )

    row["anio_usd"] = Decimal(
        january
    )

    return row


def insert_detail(
    *,
    module="CAPEX",
    row_id="row-1",
):
    return make_detail(
        (
            make_audit(
                HABILITADO_COLUMN,
                None,
                "true",
                row_id=row_id,
                value_type="BOOLEAN",
            ),
            make_audit(
                "nombre_inversion",
                None,
                "PROYECTO ERP",
                row_id=row_id,
                value_type="STRING",
            ),
            make_audit(
                "enero_usd",
                None,
                "100.00",
                row_id=row_id,
            ),
            make_audit(
                "anio_usd",
                None,
                "100.00",
                row_id=row_id,
            ),
        ),
        module=module,
    )


def test_insert_reversal_becomes_logical_disable():
    history = insert_detail()

    proposal = (
        PresupuestoReversalService
        .build_proposal(
            history,
            (
                current_row(),
            ),
            actor="PC\\Reversor",
            app_version="0.5.0",
            timestamp=NOW,
            batch_id_factory=lambda: (
                "revert-insert"
            ),
            expected_module="CAPEX",
        )
    )

    assert (
        proposal.source_batch_id
        == "source-batch"
    )

    assert (
        proposal.batch
        .reverted_batch_id
        == "source-batch"
    )

    assert proposal.row_count == 1

    # El alta original audito varios
    # campos, pero su baja logica solo
    # necesita cambiar habilitado.
    assert (
        history.batch.field_count
        == 4
    )

    assert (
        proposal.field_count
        == 1
    )

    row = proposal.batch.rows[0]

    assert row.is_update

    assert (
        row.expected_version
        == 1
    )

    assert (
        row.version_after
        == 2
    )

    assert len(
        row.field_changes
    ) == 1

    change = (
        row.field_changes[0]
    )

    assert (
        change.column
        == HABILITADO_COLUMN
    )

    assert change.before is True
    assert change.after is False

    editable = (
        row.editable_dict()
    )

    assert (
        editable[
            HABILITADO_COLUMN
        ]
        is False
    )

    # Los importes permanecen intactos.
    assert (
        editable["enero_usd"]
        == Decimal("100.00")
    )

    assert (
        editable["anio_usd"]
        == Decimal("100.00")
    )


def test_insert_reversal_blocks_later_version():
    history = insert_detail()

    with pytest.raises(
        PresupuestoReversalConflictError,
        match="despues",
    ):
        (
            PresupuestoReversalService
            .build_proposal(
                history,
                (
                    current_row(
                        version=2
                    ),
                ),
                actor="usuario",
                expected_module="CAPEX",
            )
        )


def test_insert_reversal_rejects_already_disabled_row():
    history = insert_detail()

    with pytest.raises(
        PresupuestoReversalError,
        match="deshabilitada",
    ):
        (
            PresupuestoReversalService
            .build_proposal(
                history,
                (
                    current_row(
                        enabled=False
                    ),
                ),
                actor="usuario",
                expected_module="CAPEX",
            )
        )


def test_mixed_update_and_insert_batch_is_supported():
    history = make_detail(
        (
            make_audit(
                "enero_usd",
                "100.00",
                "150.00",
                row_id="row-update",
                version_before=1,
                version_after=2,
            ),
            make_audit(
                "anio_usd",
                "100.00",
                "150.00",
                row_id="row-update",
                version_before=1,
                version_after=2,
            ),
            make_audit(
                HABILITADO_COLUMN,
                None,
                "true",
                row_id="row-insert",
                value_type="BOOLEAN",
                version_before=0,
                version_after=1,
            ),
            make_audit(
                "proveedor",
                None,
                "PROVEEDOR NUEVO",
                row_id="row-insert",
                value_type="STRING",
                version_before=0,
                version_after=1,
            ),
        ),
        module="OPEX",
    )

    proposal = (
        PresupuestoReversalService
        .build_proposal(
            history,
            (
                current_row(
                    row_id="row-update",
                    version=2,
                    january="150.00",
                ),
                current_row(
                    row_id="row-insert",
                    version=1,
                    january="25.00",
                ),
            ),
            actor="PC\\Reversor",
            timestamp=NOW,
            batch_id_factory=lambda: (
                "revert-mixed"
            ),
            expected_module="OPEX",
        )
    )

    assert (
        proposal.row_count
        == 2
    )

    # 2 cambios inversos del UPDATE
    # + 1 baja logica del INSERT.
    assert (
        proposal.field_count
        == 3
    )

    rows = {
        row.row_id: row
        for row
        in proposal.batch.rows
    }

    updated = rows[
        "row-update"
    ]

    inserted = rows[
        "row-insert"
    ]

    assert (
        updated.expected_version
        == 2
    )

    assert (
        inserted.expected_version
        == 1
    )

    assert (
        inserted.editable_dict()[
            HABILITADO_COLUMN
        ]
        is False
    )

    assert (
        len(
            inserted.field_changes
        )
        == 1
    )

    assert (
        inserted.field_changes[0]
        .column
        == HABILITADO_COLUMN
    )
