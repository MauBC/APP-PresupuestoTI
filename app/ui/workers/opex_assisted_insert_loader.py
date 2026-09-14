from typing import Callable

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
from app.services.opex_smart_inference_data_service import (
    OpexSmartInferenceDataService,
)


def build_opex_assisted_inference_service(
    module_config,
):
    bigquery = BigQueryService()

    repository = PresupuestoRepository(
        bigquery,
        module_config=module_config,
    )

    service = (
        OpexSmartInferenceDataService(
            repository
        )
    )

    service.load_snapshot()

    return service


class OpexAssistedInferenceLoadThread(
    QThread
):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        module_config,
        parent=None,
        *,
        service_factory: Callable = (
            build_opex_assisted_inference_service
        ),
    ):
        super().__init__(
            parent
        )

        self._module_config = (
            module_config
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
                    self._module_config
                )
            )

        except Exception as exc:
            self.failed.emit(
                f"{type(exc).__name__}: "
                f"{exc}"
            )
            return

        self.loaded.emit(
            service
        )
