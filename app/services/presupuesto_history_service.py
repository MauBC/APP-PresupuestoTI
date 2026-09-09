from app.models.budget_history import (
    BudgetAuditChange,
    BudgetHistoryBatch,
    BudgetHistoryDetail,
)


class PresupuestoHistoryService:
    def __init__(
        self,
        repository,
    ):
        if repository is None:
            raise ValueError(
                "repository es requerido."
            )

        self._repository = (
            repository
        )

    def list_batches(
        self,
        *,
        status: str | None = "APPLIED",
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[
        BudgetHistoryBatch,
        ...,
    ]:
        rows = (
            self._repository
            .list_batches(
                status=status,
                limit=limit,
                offset=offset,
            )
        )

        return tuple(
            BudgetHistoryBatch.from_mapping(
                row
            )
            for row
            in rows
        )

    def get_batch_detail(
        self,
        batch: BudgetHistoryBatch,
    ) -> BudgetHistoryDetail:
        if not isinstance(
            batch,
            BudgetHistoryBatch,
        ):
            raise TypeError(
                "batch debe ser "
                "BudgetHistoryBatch."
            )

        rows = (
            self._repository
            .get_batch_audit(
                batch.batch_id
            )
        )

        changes = tuple(
            BudgetAuditChange.from_mapping(
                row
            )
            for row
            in rows
        )

        return BudgetHistoryDetail(
            batch=batch,
            changes=changes,
        )
