
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
from app.services.budget_catalog_service import (
    BudgetCatalogService,
)


def catalog_columns_for_config(
    config,
):
    dimensions = set(
        config.dimension_columns
    )

    candidates = (
        config.country_column,
        config.budgeter_column,
        config.ceco_column,
        "moneda_facturacion",
        (
            "compania"
            if "compania" in dimensions
            else None
        ),
        (
            "sociedad"
            if "sociedad" in dimensions
            else None
        ),
        (
            "responsable"
            if "responsable" in dimensions
            else None
        ),
    )

    return tuple(
        dict.fromkeys(
            column
            for column in candidates
            if (
                column
                and column in dimensions
            )
        )
    )


class BudgetCatalogLoadThread(
    QThread
):
    loaded = Signal(
        object
    )

    failed = Signal(
        str
    )

    def __init__(
        self,
        module_config,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._config = (
            module_config
        )

    def run(
        self,
    ):
        try:
            bigquery_service = (
                BigQueryService()
            )

            repository = (
                PresupuestoRepository(
                    bigquery_service,
                    module_config=(
                        self._config
                    ),
                )
            )

            service = (
                BudgetCatalogService(
                    repository
                )
            )

            result = {}

            for column in (
                catalog_columns_for_config(
                    self._config
                )
            ):
                catalog = (
                    service.values(
                        column,
                        limit=500,
                    )
                )

                result[
                    column
                ] = catalog.values

            self.loaded.emit(
                result
            )

        except Exception as exc:
            self.failed.emit(
                f"{type(exc).__name__}: "
                f"{exc}"
            )
