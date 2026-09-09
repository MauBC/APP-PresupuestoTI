from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.models.budget_history import (
    BudgetAuditChange,
    BudgetHistoryBatch,
    BudgetHistoryDetail,
)
from app.models.budget_reversal import (
    BudgetReversalProposal,
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
    8,
    21,
    0,
    tzinfo=timezone.utc,
)


def make_batch(
    *,
    status="APPLIED",
    row_count=1,
    field_count=2,
    module="OPEX",
):
    return BudgetHistoryBatch(
        batch_id="source-batch",
        status=status,
        actor="PC\\Mauro",
        created_at=NOW,
        completed_at=NOW,
        row_count=row_count,
        field_count=field_count,
        app_version="0.5.0",
        error_message=None,
        budget_module=module,
    )


def audit(
    column,
    before,
    after,
    *,
    value_type="NUMERIC",
    row_id="row-1",
    version_before=1,
    version_after=2,
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
        version_before=(
            version_before
        ),
        version_after=(
            version_after
        ),
        actor="PC\\Mauro",
        changed_at=NOW,
    )


def detail(
    changes,
    *,
    status="APPLIED",
    row_count=1,
    field_count=None,
    module="OPEX",
):
    changes = tuple(
        changes
    )

    if field_count is None:
        field_count = len(
            changes
        )

    return BudgetHistoryDetail(
        batch=make_batch(
            status=status,
            row_count=row_count,
            field_count=(
                field_count
            ),
            module=module,
        ),
        changes=changes,
    )


def current_row(
    *,
    row_id="row-1",
    version=2,
    january="150.00",
    enabled=True,
):
    row = {
        "row_id": row_id,
        "version": version,
        "habilitado": enabled,
    }

    for column in (
        USD_MONTH_COLUMNS
    ):
        row[column] = Decimal(
            "0.00"
        )

    row[
        "enero_usd"
    ] = Decimal(
        january
    )

    row[
        "anio_usd"
    ] = Decimal(
        january
    )

    return row


def build_basic():
    history = detail(
        (
            audit(
                "enero_usd",
                "100.00",
                "150.00",
            ),
            audit(
                "anio_usd",
                "100.00",
                "150.00",
            ),
        )
    )

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
                "revert-batch"
            ),
            expected_module="OPEX",
        )
    )

    return (
        history,
        proposal,
    )


def test_builds_inverse_persistence_batch():
    (
        history,
        proposal,
    ) = build_basic()

    assert isinstance(
        proposal,
        BudgetReversalProposal,
    )

    assert (
        proposal.source_batch_id
        == history.batch.batch_id
    )

    assert (
        proposal.batch_id
        == "revert-batch"
    )

    assert (
        proposal.budget_module
        == "OPEX"
    )

    assert (
        proposal.batch.status
        == "PENDING"
    )

    assert (
        proposal.batch.actor
        == "PC\\Reversor"
    )

    assert (
        proposal.batch.reverted_batch_id
        == "source-batch"
    )

    assert proposal.row_count == 1
    assert proposal.field_count == 2

    row = (
        proposal.batch.rows[
            0
        ]
    )

    assert row.row_id == "row-1"

    assert (
        row.expected_version
        == 2
    )

    assert (
        row.version_after
        == 3
    )

    by_column = {
        change.column:
            change
        for change
        in row.field_changes
    }

    january = by_column[
        "enero_usd"
    ]

    assert (
        january.before
        == Decimal("150.00")
    )

    assert (
        january.after
        == Decimal("100.00")
    )

    annual = by_column[
        "anio_usd"
    ]

    assert (
        annual.before
        == Decimal("150.00")
    )

    assert (
        annual.after
        == Decimal("100.00")
    )

    editable = (
        row.editable_dict()
    )

    assert (
        editable[
            "enero_usd"
        ]
        == Decimal("100.00")
    )

    assert (
        editable[
            "anio_usd"
        ]
        == Decimal("100.00")
    )


def test_boolean_change_is_reversed():
    history = detail(
        (
            audit(
                "habilitado",
                "true",
                "false",
                value_type="BOOLEAN",
            ),
        ),
        field_count=1,
    )

    row = current_row(
        enabled=False
    )

    proposal = (
        PresupuestoReversalService
        .build_proposal(
            history,
            (row,),
            actor="usuario",
            timestamp=NOW,
            batch_id_factory=lambda: (
                "revert-enable"
            ),
        )
    )

    change = (
        proposal.batch.rows[
            0
        ].field_changes[0]
    )

    assert (
        change.column
        == "habilitado"
    )

    assert change.before is False
    assert change.after is True

    assert (
        proposal.batch.rows[
            0
        ].editable_dict()[
            "habilitado"
        ]
        is True
    )


def test_non_applied_batch_is_rejected():
    history = detail(
        (
            audit(
                "enero_usd",
                "100.00",
                "150.00",
            ),
        ),
        status="CONFLICT",
    )

    with pytest.raises(
        PresupuestoReversalError,
        match="APPLIED",
    ):
        (
            PresupuestoReversalService
            .build_proposal(
                history,
                (
                    current_row(),
                ),
                actor="usuario",
            )
        )


def test_incomplete_audit_is_rejected():
    history = detail(
        (
            audit(
                "enero_usd",
                "100.00",
                "150.00",
            ),
        ),
        field_count=2,
    )

    with pytest.raises(
        PresupuestoReversalError,
        match="field_count",
    ):
        (
            PresupuestoReversalService
            .build_proposal(
                history,
                (
                    current_row(),
                ),
                actor="usuario",
            )
        )


def test_later_version_is_conflict():
    history = detail(
        (
            audit(
                "enero_usd",
                "100.00",
                "150.00",
            ),
            audit(
                "anio_usd",
                "100.00",
                "150.00",
            ),
        )
    )

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
                        version=3
                    ),
                ),
                actor="usuario",
            )
        )


def test_changed_current_value_is_conflict():
    history = detail(
        (
            audit(
                "enero_usd",
                "100.00",
                "150.00",
            ),
            audit(
                "anio_usd",
                "100.00",
                "150.00",
            ),
        )
    )

    row = current_row()

    row[
        "enero_usd"
    ] = Decimal(
        "149.00"
    )

    with pytest.raises(
        PresupuestoReversalConflictError,
        match="valor actual",
    ):
        (
            PresupuestoReversalService
            .build_proposal(
                history,
                (row,),
                actor="usuario",
            )
        )


def test_missing_current_row_is_conflict():
    history = detail(
        (
            audit(
                "enero_usd",
                "100.00",
                "150.00",
            ),
            audit(
                "anio_usd",
                "100.00",
                "150.00",
            ),
        )
    )

    with pytest.raises(
        PresupuestoReversalConflictError,
        match="Faltan",
    ):
        (
            PresupuestoReversalService
            .build_proposal(
                history,
                (),
                actor="usuario",
            )
        )


def test_duplicate_current_row_is_rejected():
    history = detail(
        (
            audit(
                "enero_usd",
                "100.00",
                "150.00",
            ),
            audit(
                "anio_usd",
                "100.00",
                "150.00",
            ),
        )
    )

    row = current_row()

    with pytest.raises(
        PresupuestoReversalError,
        match="duplicados",
    ):
        (
            PresupuestoReversalService
            .build_proposal(
                history,
                (
                    row,
                    row,
                ),
                actor="usuario",
            )
        )


def test_wrong_value_type_is_rejected():
    history = detail(
        (
            audit(
                "enero_usd",
                "100.00",
                "150.00",
                value_type="BOOLEAN",
            ),
        )
    )

    with pytest.raises(
        PresupuestoReversalError,
        match="value_type",
    ):
        (
            PresupuestoReversalService
            .build_proposal(
                history,
                (
                    current_row(),
                ),
                actor="usuario",
            )
        )


def test_inconsistent_versions_are_rejected():
    history = detail(
        (
            audit(
                "enero_usd",
                "100.00",
                "150.00",
                version_before=1,
                version_after=2,
            ),
            audit(
                "anio_usd",
                "100.00",
                "150.00",
                version_before=2,
                version_after=3,
            ),
        )
    )

    with pytest.raises(
        PresupuestoReversalError,
        match="versiones inconsistentes",
    ):
        (
            PresupuestoReversalService
            .build_proposal(
                history,
                (
                    current_row(),
                ),
                actor="usuario",
            )
        )


def test_inconsistent_annual_target_is_rejected():
    history = detail(
        (
            audit(
                "enero_usd",
                "90.00",
                "150.00",
            ),
            audit(
                "anio_usd",
                "100.00",
                "150.00",
            ),
        )
    )

    with pytest.raises(
        PresupuestoReversalError,
        match="total anual inconsistente",
    ):
        (
            PresupuestoReversalService
            .build_proposal(
                history,
                (
                    current_row(),
                ),
                actor="usuario",
            )
        )


def test_module_mismatch_is_rejected():
    history = detail(
        (
            audit(
                "enero_usd",
                "100.00",
                "150.00",
            ),
            audit(
                "anio_usd",
                "100.00",
                "150.00",
            ),
        ),
        module="OPEX",
    )

    with pytest.raises(
        PresupuestoReversalError,
        match="modulo OPEX",
    ):
        (
            PresupuestoReversalService
            .build_proposal(
                history,
                (
                    current_row(),
                ),
                actor="usuario",
                expected_module=(
                    "CAPEX"
                ),
            )
        )


def test_new_batch_id_cannot_equal_source():
    history = detail(
        (
            audit(
                "enero_usd",
                "100.00",
                "150.00",
            ),
            audit(
                "anio_usd",
                "100.00",
                "150.00",
            ),
        )
    )

    with pytest.raises(
        PresupuestoReversalError,
        match="batch_id",
    ):
        (
            PresupuestoReversalService
            .build_proposal(
                history,
                (
                    current_row(),
                ),
                actor="usuario",
                timestamp=NOW,
                batch_id_factory=lambda: (
                    "source-batch"
                ),
            )
        )
