from app.models.budget_history import (
    BudgetAuditChange,
    BudgetHistoryBatch,
    BudgetHistoryDetail,
    BudgetHistoryRowContext,
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

        module_config = getattr(
            self._repository,
            "module_config",
            None,
        )

        context_columns = tuple(
            getattr(
                module_config,
                "change_detail_columns",
                (),
            )
            or ()
        )

        row_contexts = ()

        context_reader = getattr(
            self._repository,
            "get_history_row_context",
            None,
        )

        if (
            callable(context_reader)
            and changes
            and context_columns
        ):
            row_ids = tuple(
                dict.fromkeys(
                    change.row_id
                    for change
                    in changes
                )
            )

            context_rows = (
                context_reader(
                    row_ids
                )
            )

            row_contexts = tuple(
                BudgetHistoryRowContext
                .from_mapping(
                    row,
                    context_columns,
                )
                for row
                in context_rows
            )

        return BudgetHistoryDetail(
            batch=batch,
            changes=changes,
            context_columns=(
                context_columns
            ),
            row_contexts=(
                row_contexts
            ),
        )
