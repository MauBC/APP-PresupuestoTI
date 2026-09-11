
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import (
    QThread,
    Signal,
)

from app.services.capex_sharepoint_sync_service import (
    CapexSharePointSyncService,
)
from app.services.sharepoint_summary_publisher import (
    SharePointLargeDeleteGuardError,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SharePointSummarySyncThreadFailure:
    message: str
    source_batch_id: str | None
    requires_large_delete_confirmation: bool = False
    create_count: int = 0
    update_count: int = 0
    delete_count: int = 0
    unchanged_count: int = 0
    unmanaged_count: int = 0
    current_item_count: int = 0
    desired_item_count: int = 0


class CapexSharePointSummarySyncThread(
    QThread
):
    completed = Signal(
        object
    )

    failed = Signal(
        object
    )

    def __init__(
        self,
        *,
        source_batch_id=None,
        parent=None,
        allow_large_delete=False,
        service_factory:
            Callable[
                [],
                CapexSharePointSyncService,
            ]
            = CapexSharePointSyncService,
    ):
        super().__init__(
            parent
        )

        value = (
            str(
                source_batch_id
            ).strip()
            if source_batch_id
            is not None
            else None
        )

        self._source_batch_id = (
            value or None
        )

        self._allow_large_delete = bool(
            allow_large_delete
        )

        self._service_factory = (
            service_factory
        )

    def run(
        self,
    ):
        preparation = None

        try:
            service = (
                self._service_factory()
            )

            preparation = (
                service.prepare()
            )

            outcome = (
                service.publish(
                    preparation,
                    source_batch_id=(
                        self._source_batch_id
                    ),
                    allow_large_delete=(
                        self._allow_large_delete
                    ),
                )
            )

        except SharePointLargeDeleteGuardError as exc:
            plan = (
                preparation.plan
                if preparation is not None
                else None
            )

            self.failed.emit(
                SharePointSummarySyncThreadFailure(
                    message=(
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                    source_batch_id=(
                        self._source_batch_id
                    ),
                    requires_large_delete_confirmation=True,
                    create_count=(
                        plan.create_count
                        if plan is not None
                        else 0
                    ),
                    update_count=(
                        plan.update_count
                        if plan is not None
                        else 0
                    ),
                    delete_count=(
                        plan.delete_count
                        if plan is not None
                        else 0
                    ),
                    unchanged_count=(
                        plan.unchanged_count
                        if plan is not None
                        else 0
                    ),
                    unmanaged_count=(
                        plan.unmanaged_count
                        if plan is not None
                        else 0
                    ),
                    current_item_count=(
                        plan.current_item_count
                        if plan is not None
                        else 0
                    ),
                    desired_item_count=(
                        plan.desired_item_count
                        if plan is not None
                        else 0
                    ),
                )
            )

            return

        except Exception as exc:
            self.failed.emit(
                SharePointSummarySyncThreadFailure(
                    message=(
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                    source_batch_id=(
                        self._source_batch_id
                    ),
                )
            )

            return

        self.completed.emit(
            outcome
        )
