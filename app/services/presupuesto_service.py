from app.models.page_result import PageResult
from app.repositories.presupuesto_repository import (
    PresupuestoRepository,
)


class PresupuestoService:
    MAX_PAGE_SIZE = 1000

    def __init__(
        self,
        repository: PresupuestoRepository,
    ):
        self._repository = repository

    def get_page(
        self,
        page_index: int,
        page_size: int,
    ) -> PageResult:
        if page_index < 0:
            raise ValueError(
                "El indice de pagina no puede ser negativo."
            )

        if page_size < 1:
            raise ValueError(
                "El tamano de pagina debe ser mayor que cero."
            )

        if page_size > self.MAX_PAGE_SIZE:
            raise ValueError(
                "El tamano de pagina no puede superar "
                f"{self.MAX_PAGE_SIZE} registros."
            )

        offset = page_index * page_size

        return self._repository.get_page(
            limit=page_size,
            offset=offset,
        )