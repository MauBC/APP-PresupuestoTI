from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceFieldChange:
    column: str
    before: Any
    after: Any
    value_type: str


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceRowChange:
    row_id: str
    expected_version: int
    field_changes: tuple[
        PersistenceFieldChange,
        ...
    ]
    editable_values: tuple[
        tuple[str, Any],
        ...
    ]

    @property
    def version_after(self) -> int:
        return (
            self.expected_version
            + 1
        )

    @property
    def field_count(self) -> int:
        return len(
            self.field_changes
        )

    def editable_dict(
        self,
    ) -> dict[str, Any]:
        return dict(
            self.editable_values
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceBatch:
    batch_id: str
    status: str
    actor: str
    created_at: datetime
    app_version: str | None
    rows: tuple[
        PersistenceRowChange,
        ...
    ]

    @property
    def row_count(self) -> int:
        return len(
            self.rows
        )

    @property
    def field_count(self) -> int:
        return sum(
            row.field_count
            for row in self.rows
        )


@dataclass(
    frozen=True,
    slots=True,
)
class StagingRow:
    batch_id: str
    row_id: str
    expected_version: int
    editable_values: tuple[
        tuple[str, Any],
        ...
    ]
    staged_at: datetime

    def as_record(
        self,
    ) -> dict[str, Any]:
        record = {
            "batch_id": self.batch_id,
            "row_id": self.row_id,
            "expected_version": (
                self.expected_version
            ),
        }

        record.update(
            self.editable_values
        )

        record[
            "staged_at"
        ] = self.staged_at

        return record
