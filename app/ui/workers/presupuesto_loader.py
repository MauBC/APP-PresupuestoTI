from PySide6.QtCore import (
    QThread,
    Signal,
)

from app.repositories.presupuesto_repository import (
    PresupuestoRepository,
)
from app.services.bigquery_service import (
    BigQueryService,
)
from app.services.presupuesto_service import (
    PresupuestoService,
)


class PresupuestoLoadThread(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        page_index: int,
        page_size: int,
        parent=None,
    ):
        super().__init__(parent)

        self._page_index = page_index
        self._page_size = page_size

    def run(self):
        try:
            bigquery = BigQueryService()

            repository = (
                PresupuestoRepository(
                    bigquery
                )
            )

            service = PresupuestoService(
                repository
            )

            result = service.get_page(
                page_index=self._page_index,
                page_size=self._page_size,
            )

            self.loaded.emit(
                result
            )

        except Exception as exc:
            self.failed.emit(
                f"{type(exc).__name__}: {exc}"
            )