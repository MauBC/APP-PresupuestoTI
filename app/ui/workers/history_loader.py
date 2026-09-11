from typing import Callable

from PySide6.QtCore import (
    QThread,
    Signal,
)

from app.services.bigquery_service import (
    BigQueryService,
)
from app.services.presupuesto_history_service import (
    PresupuestoHistoryService,
)
from database.persistence.bigquery_repository import (
    BigQueryPersistenceRepository,
)


def build_history_service(
    module_config,
) -> PresupuestoHistoryService:
    bigquery = BigQueryService()

    repository = (
        BigQueryPersistenceRepository(
            bigquery.client,
            module_config=module_config,
        )
    )

    return PresupuestoHistoryService(
        repository
    )


class HistoryLoadThread(
    QThread
):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        module_config,
        *,
        status: str | None = "APPLIED",
        limit: int = 200,
        offset: int = 0,
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

        self._status = status
        self._limit = limit
        self._offset = offset

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

            batches = (
                service.list_batches(
                    status=self._status,
                    limit=self._limit,
                    offset=self._offset,
                )
            )

            self.loaded.emit(
                batches
            )

        except Exception as exc:
            self.failed.emit(
                f"{type(exc).__name__}: {exc}"
            )
