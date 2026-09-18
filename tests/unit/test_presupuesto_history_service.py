from datetime import (
    datetime,
    timezone,
)

import pytest

from app.models.budget_history import (
    BudgetAuditChange,
    BudgetHistoryBatch,
    BudgetHistoryDetail,
)

from app.services.presupuesto_history_service import (
    PresupuestoHistoryService,
)


pytestmark = pytest.mark.unit


CREATED_AT = datetime(
    2026,
    9,
    8,
    20,
    0,
    tzinfo=timezone.utc,
)

COMPLETED_AT = datetime(
    2026,
    9,
    8,
    20,
    1,
    tzinfo=timezone.utc,
)


def batch_row(
    *,
    batch_id="batch-001",
    status="APPLIED",
    row_count=1,
    field_count=2,
    is_insert=False,
):
    return {
        "batch_id": batch_id,
        "status": status,
        "actor": (
            "PC-TEST\\usuario"
        ),
        "created_at": CREATED_AT,
        "completed_at":
            COMPLETED_AT,
        "row_count": row_count,
        "field_count":
            field_count,
        "app_version": "0.5.0",
        "error_message": None,
        "budget_module": "OPEX",
        "reverted_batch_id": None,
        "is_insert": is_insert,
    }


def audit_row(
    *,
    audit_id,
    column_name,
    batch_id="batch-001",
    row_id="row-001",
    version_before=1,
    version_after=2,
):
    return {
        "audit_id": audit_id,
        "batch_id": batch_id,
        "row_id": row_id,
        "column_name":
            column_name,
        "value_type": "NUMERIC",
        "before_value": "100.00",
        "after_value": "110.00",
        "version_before":
            version_before,
        "version_after":
            version_after,
        "actor": (
            "PC-TEST\\usuario"
        ),
        "changed_at": CREATED_AT,
    }


class FakeHistoryRepository:
    def __init__(
        self,
        *,
        batches=(),
        audits=None,
    ):
        self.batches = tuple(
            batches
        )

        self.audits = (
            audits
            if audits is not None
            else {}
        )

        self.list_calls = []
        self.audit_calls = []

    def list_batches(
        self,
        *,
        status,
        limit,
        offset,
    ):
        self.list_calls.append(
            {
                "status": status,
                "limit": limit,
                "offset": offset,
            }
        )

        return self.batches

    def get_batch_audit(
        self,
        batch_id,
    ):
        self.audit_calls.append(
            batch_id
        )

        return tuple(
            self.audits.get(
                batch_id,
                (),
            )
        )


def test_history_batch_from_mapping():
    batch = (
        BudgetHistoryBatch
        .from_mapping(
            batch_row()
        )
    )

    assert (
        batch.batch_id
        == "batch-001"
    )

    assert batch.is_applied

    assert batch.row_count == 1
    assert batch.field_count == 2

    assert (
        batch.budget_module
        == "OPEX"
    )

    assert (
        batch.reverted_batch_id
        is None
    )


def test_history_batch_maps_insert_flag():
    item = (
        BudgetHistoryBatch
        .from_mapping(
            batch_row(
                is_insert=True
            )
        )
    )

    assert item.is_insert is True


def test_history_service_lists_typed_batches():
    repository = (
        FakeHistoryRepository(
            batches=(
                batch_row(),
            )
        )
    )

    service = (
        PresupuestoHistoryService(
            repository
        )
    )

    batches = service.list_batches(
        limit=25,
        offset=50,
    )

    assert len(batches) == 1

    assert isinstance(
        batches[0],
        BudgetHistoryBatch,
    )

    assert repository.list_calls == [
        {
            "status": "APPLIED",
            "limit": 25,
            "offset": 50,
        }
    ]


def test_history_service_can_request_all_statuses():
    repository = (
        FakeHistoryRepository(
            batches=(
                batch_row(
                    status="CONFLICT"
                ),
            )
        )
    )

    service = (
        PresupuestoHistoryService(
            repository
        )
    )

    batches = service.list_batches(
        status=None
    )

    assert (
        batches[0].status
        == "CONFLICT"
    )

    assert not (
        batches[0].is_applied
    )

    assert (
        repository.list_calls[
            0
        ]["status"]
        is None
    )


def test_batch_detail_is_typed_and_complete():
    repository = (
        FakeHistoryRepository(
            batches=(
                batch_row(),
            ),
            audits={
                "batch-001": (
                    audit_row(
                        audit_id=(
                            "audit-001"
                        ),
                        column_name=(
                            "enero_usd"
                        ),
                    ),
                    audit_row(
                        audit_id=(
                            "audit-002"
                        ),
                        column_name=(
                            "anio_usd"
                        ),
                    ),
                )
            },
        )
    )

    service = (
        PresupuestoHistoryService(
            repository
        )
    )

    batch = (
        service.list_batches()[0]
    )

    detail = (
        service.get_batch_detail(
            batch
        )
    )

    assert isinstance(
        detail,
        BudgetHistoryDetail,
    )

    assert all(
        isinstance(
            change,
            BudgetAuditChange,
        )
        for change
        in detail.changes
    )

    assert detail.audit_count == 2

    assert (
        detail.row_ids
        == (
            "row-001",
        )
    )

    assert (
        detail.audited_row_count
        == 1
    )

    assert (
        detail.field_count_matches
    )

    assert (
        detail.row_count_matches
    )

    assert (
        detail.version_pairs
        == (
            (1, 2),
        )
    )

    assert (
        repository.audit_calls
        == [
            "batch-001"
        ]
    )


def test_detail_detects_incomplete_audit():
    batch = (
        BudgetHistoryBatch
        .from_mapping(
            batch_row(
                field_count=2
            )
        )
    )

    change = (
        BudgetAuditChange
        .from_mapping(
            audit_row(
                audit_id="audit-001",
                column_name=(
                    "enero_usd"
                ),
            )
        )
    )

    detail = BudgetHistoryDetail(
        batch=batch,
        changes=(
            change,
        ),
    )

    assert not (
        detail.field_count_matches
    )

    assert (
        detail.row_count_matches
    )


def test_detail_detects_row_count_mismatch():
    batch = (
        BudgetHistoryBatch
        .from_mapping(
            batch_row(
                row_count=2,
                field_count=1,
            )
        )
    )

    change = (
        BudgetAuditChange
        .from_mapping(
            audit_row(
                audit_id="audit-001",
                column_name=(
                    "enero_usd"
                ),
            )
        )
    )

    detail = BudgetHistoryDetail(
        batch=batch,
        changes=(
            change,
        ),
    )

    assert (
        detail.field_count_matches
    )

    assert not (
        detail.row_count_matches
    )


def test_detail_rejects_audit_from_other_batch():
    batch = (
        BudgetHistoryBatch
        .from_mapping(
            batch_row()
        )
    )

    foreign_change = (
        BudgetAuditChange
        .from_mapping(
            audit_row(
                audit_id="audit-x",
                column_name=(
                    "enero_usd"
                ),
                batch_id=(
                    "other-batch"
                ),
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="otro batch",
    ):
        BudgetHistoryDetail(
            batch=batch,
            changes=(
                foreign_change,
            ),
        )


def test_history_service_rejects_wrong_batch_type():
    service = (
        PresupuestoHistoryService(
            FakeHistoryRepository()
        )
    )

    with pytest.raises(
        TypeError,
        match="BudgetHistoryBatch",
    ):
        service.get_batch_detail(
            "batch-001"
        )
