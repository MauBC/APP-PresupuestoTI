
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldChange:
    column: str
    before: Any
    after: Any


@dataclass(frozen=True)
class PendingRowChange:
    session_row_id: int
    changes: tuple[FieldChange, ...]


@dataclass(frozen=True)
class RowStateChange:
    session_row_id: int
    before: dict[str, Any] | None
    after: dict[str, Any]


@dataclass(frozen=True)
class ChangeBatch:
    description: str
    rows: tuple[RowStateChange, ...]
