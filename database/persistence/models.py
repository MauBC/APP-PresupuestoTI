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

    completed_at: datetime | None = None
    error_message: str | None = None
    reverted_batch_id: str | None = None

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


@dataclass(
    frozen=True,
    slots=True,
)
class AuditChange:
    audit_id: str
    batch_id: str
    row_id: str
    column_name: str
    value_type: str

    before_value: str | None
    after_value: str | None

    version_before: int
    version_after: int

    actor: str
    changed_at: datetime

    def as_record(
        self,
    ) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "batch_id": self.batch_id,
            "row_id": self.row_id,
            "column_name": self.column_name,
            "value_type": self.value_type,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "version_before": (
                self.version_before
            ),
            "version_after": (
                self.version_after
            ),
            "actor": self.actor,
            "changed_at": self.changed_at,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class ConflictDetail:
    row_id: str
    expected_version: int
    current_version: int | None


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceResult:
    batch_id: str
    status: str
    row_count: int
    field_count: int

    conflicts: tuple[
        ConflictDetail,
        ...
    ] = ()

    error_message: str | None = None

    @property
    def is_applied(self) -> bool:
        return (
            self.status
            == "APPLIED"
        )

    @property
    def has_conflicts(self) -> bool:
        return bool(
            self.conflicts
        )
