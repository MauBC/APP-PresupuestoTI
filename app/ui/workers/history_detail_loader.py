from typing import Callable

from PySide6.QtCore import (
    QThread,
    Signal,
)

from app.ui.workers.history_loader import (
    build_history_service,
)


class HistoryDetailLoadThread(
    QThread
):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        module_config,
        batch,
        *,
        parent=None,
        service_factory: Callable = (
            build_history_service
        ),
    ):
        super().__init__(
            parent
        )

        self._module_config = (
            module_config
        )

        self._batch = batch

        self._service_factory = (
            service_factory
        )

    def run(
        self,
    ):
        try:
            service = (
                self._service_factory(
                    self._module_config
                )
            )

            detail = (
                service.get_batch_detail(
                    self._batch
                )
            )

            self.loaded.emit(
                detail
            )

        except Exception as exc:
            self.failed.emit(
                f"{type(exc).__name__}: {exc}"
            )
