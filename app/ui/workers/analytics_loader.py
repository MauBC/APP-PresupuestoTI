from PySide6.QtCore import (
    QThread,
    Signal,
)

from app.repositories.presupuesto_repository import (
    PresupuestoRepository,
)
from app.services.bigquery_service import BigQueryService
from app.services.presupuesto_analysis_service import (
    PresupuestoAnalysisService,
)


class AggregationLoadThread(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        group_columns,
        parent=None,
    ):
        super().__init__(parent)

        self._group_columns = tuple(
            group_columns
        )

    def run(self):
        try:
            bigquery = BigQueryService()

            repository = PresupuestoRepository(
                bigquery
            )

            service = PresupuestoAnalysisService(
                repository
            )

            result = service.get_grouped_totals(
                self._group_columns
            )

            self.loaded.emit(result)

        except Exception as exc:
            self.failed.emit(
                f"{type(exc).__name__}: {exc}"
            )


class DashboardLoadThread(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            bigquery = BigQueryService()

            repository = PresupuestoRepository(
                bigquery
            )

            service = PresupuestoAnalysisService(
                repository
            )

            result = service.get_dashboard()

            self.loaded.emit(result)

        except Exception as exc:
            self.failed.emit(
                f"{type(exc).__name__}: {exc}"
            )