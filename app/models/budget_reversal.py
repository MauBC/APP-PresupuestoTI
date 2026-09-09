from dataclasses import dataclass

from database.persistence.models import (
    PersistenceBatch,
)


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetReversalProposal:
    source_batch_id: str
    budget_module: str
    batch: PersistenceBatch

    def __post_init__(
        self,
    ) -> None:
        if not self.source_batch_id.strip():
            raise ValueError(
                "source_batch_id no puede "
                "estar vacio."
            )

        if not self.budget_module.strip():
            raise ValueError(
                "budget_module no puede "
                "estar vacio."
            )

        if (
            self.batch.reverted_batch_id
            != self.source_batch_id
        ):
            raise ValueError(
                "El PersistenceBatch no "
                "referencia el batch original."
            )

    @property
    def batch_id(
        self,
    ) -> str:
        return self.batch.batch_id

    @property
    def row_count(
        self,
    ) -> int:
        return self.batch.row_count

    @property
    def field_count(
        self,
    ) -> int:
        return self.batch.field_count

    @property
    def row_ids(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            row.row_id
            for row
            in self.batch.rows
        )
