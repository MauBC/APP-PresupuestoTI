from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class NewBudgetRowDraft:
    module: str
    row: dict[str, Any]

    @property
    def row_id(
        self,
    ) -> str:
        return str(
            self.row["row_id"]
        )

    @property
    def version(
        self,
    ) -> int:
        return int(
            self.row["version"]
        )

    @property
    def enabled(
        self,
    ) -> bool:
        return bool(
            self.row["habilitado"]
        )
