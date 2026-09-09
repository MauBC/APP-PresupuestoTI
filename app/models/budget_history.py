from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


def _required_text(
    value: Any,
    field_name: str,
) -> str:
    text = str(
        value
        if value is not None
        else ""
    ).strip()

    if not text:
        raise ValueError(
            f"{field_name} no puede estar vacio."
        )

    return text


def _optional_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetHistoryBatch:
    batch_id: str
    status: str
    actor: str
    created_at: datetime
    completed_at: datetime | None
    row_count: int
    field_count: int
    app_version: str | None
    error_message: str | None
    budget_module: str

    def __post_init__(
        self,
    ) -> None:
        if not self.batch_id.strip():
            raise ValueError(
                "batch_id no puede estar vacio."
            )

        if not self.status.strip():
            raise ValueError(
                "status no puede estar vacio."
            )

        if not self.actor.strip():
            raise ValueError(
                "actor no puede estar vacio."
            )

        if not self.budget_module.strip():
            raise ValueError(
                "budget_module no puede estar vacio."
            )

        if self.row_count < 0:
            raise ValueError(
                "row_count no puede ser negativo."
            )

        if self.field_count < 0:
            raise ValueError(
                "field_count no puede ser negativo."
            )

    @property
    def is_applied(
        self,
    ) -> bool:
        return (
            self.status
            .strip()
            .upper()
            == "APPLIED"
        )

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[
            str,
            Any,
        ],
    ) -> "BudgetHistoryBatch":
        return cls(
            batch_id=_required_text(
                data.get("batch_id"),
                "batch_id",
            ),
            status=_required_text(
                data.get("status"),
                "status",
            ),
            actor=_required_text(
                data.get("actor"),
                "actor",
            ),
            created_at=data[
                "created_at"
            ],
            completed_at=data.get(
                "completed_at"
            ),
            row_count=int(
                data.get(
                    "row_count",
                    0,
                )
                or 0
            ),
            field_count=int(
                data.get(
                    "field_count",
                    0,
                )
                or 0
            ),
            app_version=_optional_text(
                data.get(
                    "app_version"
                )
            ),
            error_message=_optional_text(
                data.get(
                    "error_message"
                )
            ),
            budget_module=_required_text(
                data.get(
                    "budget_module"
                ),
                "budget_module",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetAuditChange:
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

    def __post_init__(
        self,
    ) -> None:
        required = (
            (
                "audit_id",
                self.audit_id,
            ),
            (
                "batch_id",
                self.batch_id,
            ),
            (
                "row_id",
                self.row_id,
            ),
            (
                "column_name",
                self.column_name,
            ),
            (
                "value_type",
                self.value_type,
            ),
            (
                "actor",
                self.actor,
            ),
        )

        for field_name, value in required:
            if not value.strip():
                raise ValueError(
                    f"{field_name} no puede "
                    "estar vacio."
                )

        if self.version_before < 1:
            raise ValueError(
                "version_before debe ser "
                "mayor o igual a 1."
            )

        if self.version_after < 1:
            raise ValueError(
                "version_after debe ser "
                "mayor o igual a 1."
            )

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[
            str,
            Any,
        ],
    ) -> "BudgetAuditChange":
        return cls(
            audit_id=_required_text(
                data.get("audit_id"),
                "audit_id",
            ),
            batch_id=_required_text(
                data.get("batch_id"),
                "batch_id",
            ),
            row_id=_required_text(
                data.get("row_id"),
                "row_id",
            ),
            column_name=_required_text(
                data.get(
                    "column_name"
                ),
                "column_name",
            ),
            value_type=_required_text(
                data.get(
                    "value_type"
                ),
                "value_type",
            ),
            before_value=_optional_text(
                data.get(
                    "before_value"
                )
            ),
            after_value=_optional_text(
                data.get(
                    "after_value"
                )
            ),
            version_before=int(
                data[
                    "version_before"
                ]
            ),
            version_after=int(
                data[
                    "version_after"
                ]
            ),
            actor=_required_text(
                data.get("actor"),
                "actor",
            ),
            changed_at=data[
                "changed_at"
            ],
        )


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetHistoryDetail:
    batch: BudgetHistoryBatch
    changes: tuple[
        BudgetAuditChange,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        for change in self.changes:
            if (
                change.batch_id
                != self.batch.batch_id
            ):
                raise ValueError(
                    "El detalle contiene un "
                    "audit de otro batch."
                )

    @property
    def audit_count(
        self,
    ) -> int:
        return len(
            self.changes
        )

    @property
    def row_ids(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            dict.fromkeys(
                change.row_id
                for change
                in self.changes
            )
        )

    @property
    def audited_row_count(
        self,
    ) -> int:
        return len(
            self.row_ids
        )

    @property
    def field_count_matches(
        self,
    ) -> bool:
        return (
            self.audit_count
            == self.batch.field_count
        )

    @property
    def row_count_matches(
        self,
    ) -> bool:
        return (
            self.audited_row_count
            == self.batch.row_count
        )

    @property
    def version_pairs(
        self,
    ) -> tuple[
        tuple[
            int,
            int,
        ],
        ...,
    ]:
        return tuple(
            dict.fromkeys(
                (
                    change.version_before,
                    change.version_after,
                )
                for change
                in self.changes
            )
        )
