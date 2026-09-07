from app.config.presupuesto_app_config import (
    GROUPABLE_COLUMNS,
)
from app.repositories.presupuesto_repository import (
    PresupuestoRepository,
)


class PresupuestoAnalysisService:
    MAX_GROUP_COLUMNS = 3

    def __init__(
        self,
        repository: PresupuestoRepository,
    ):
        self._repository = repository

    def get_grouped_totals(
        self,
        group_columns,
    ):
        columns = tuple(group_columns)

        if not columns:
            raise ValueError(
                "Debe seleccionar al menos una columna."
            )

        if (
            len(columns)
            > self.MAX_GROUP_COLUMNS
        ):
            raise ValueError(
                "Solo se permiten hasta "
                f"{self.MAX_GROUP_COLUMNS} "
                "niveles de agrupacion."
            )

        if len(columns) != len(set(columns)):
            raise ValueError(
                "No se puede repetir una columna "
                "en la agrupacion."
            )

        allowed_columns = set(
            GROUPABLE_COLUMNS
        )

        invalid_columns = [
            column
            for column in columns
            if column not in allowed_columns
        ]

        if invalid_columns:
            raise ValueError(
                "Columnas de agrupacion no validas: "
                + ", ".join(invalid_columns)
            )

        return self._repository.get_grouped_totals(
            columns
        )

    def get_dashboard(self):
        return self._repository.get_dashboard()