
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import (
    QThread,
    Signal,
)

from app.services.capex_sharepoint_sync_service import (
    CapexSharePointSyncService,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SharePointSummarySyncThreadFailure:
    message: str
    source_batch_id: str | None


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

        self._service_factory = (
            service_factory
        )

    def run(
        self,
    ):
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
                )
            )

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
