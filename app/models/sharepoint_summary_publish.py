
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class SharePointSummaryPublishResult:
    sync_run_id: str
    source_batch_id: str | None
    updated_at: datetime

    created_count: int
    updated_count: int
    deleted_count: int

    @property
    def write_count(
        self,
    ) -> int:
        return (
            self.created_count
            + self.updated_count
            + self.deleted_count
        )


@dataclass(
    frozen=True,
    slots=True,
)
class CapexSharePointSyncPreparation:
    summary_result: Any

    desired_items: tuple[
        Any,
        ...
    ]

    current_items: tuple[
        dict,
        ...
    ]

    plan: Any


@dataclass(
    frozen=True,
    slots=True,
)
class CapexSharePointSyncOutcome:
    preparation: CapexSharePointSyncPreparation

    publish_result: SharePointSummaryPublishResult

    verification_plan: Any
