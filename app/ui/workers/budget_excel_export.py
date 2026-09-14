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
from app.services.budget_excel_export_service import (
    BudgetExcelExportService,
)


def build_budget_excel_export_service(
    module_config,
):
    bigquery_service = (
        BigQueryService()
    )

    repository = (
        PresupuestoRepository(
            bigquery_service,
            module_config=(
                module_config
            ),
        )
    )

    return (
        BudgetExcelExportService(
            repository,
            module_config=(
                module_config
            ),
        )
    )


class BudgetExcelExportThread(
    QThread
):
    exported = Signal(
        object
    )

    failed = Signal(
        str
    )

    def __init__(
        self,
        *,
        module_config,
        destination,
        parent=None,
        service_factory=(
            build_budget_excel_export_service
        ),
    ):
        super().__init__(
            parent
        )

        self._config = (
            module_config
        )

        self._destination = str(
            destination
        )

        self._service_factory = (
            service_factory
        )

    def run(
        self,
    ):
        try:
            service = (
                self._service_factory(
                    self._config
                )
            )

            result = (
                service.export(
                    self._destination
                )
            )

        except Exception as exc:
            self.failed.emit(
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            return

        self.exported.emit(
            result
        )
