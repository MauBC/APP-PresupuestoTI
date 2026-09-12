from PySide6.QtCore import (
    QThread,
    Signal,
)


class OpexSmartImportWorker(
    QThread
):
    succeeded = Signal(
        object
    )

    failed = Signal(
        str
    )

    def __init__(
        self,
        *,
        service,
        source_path,
        origin,
        budgeter,
        actor,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._service = service
        self._source_path = source_path
        self._origin = origin
        self._budgeter = budgeter
        self._actor = actor

    def run(
        self,
    ):
        try:
            result = (
                self._service
                .prepare(
                    source_path=(
                        self._source_path
                    ),
                    origin=self._origin,
                    budgeter=self._budgeter,
                    actor=self._actor,
                )
            )

        except Exception as exc:
            self.failed.emit(
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            return

        self.succeeded.emit(
            result
        )
