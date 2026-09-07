from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from app.services.presupuesto_persistence_service import (
    PresupuestoPersistenceService,
)
from app.services.presupuesto_workspace_loader import (
    PresupuestoWorkspaceLoader,
    WorkspaceLoadResult,
)
from database.persistence.batch_builder import (
    generate_batch_id,
)
from database.persistence.models import (
    PersistenceResult,
)


@dataclass(frozen=True)
class PresupuestoSaveOutcome:
    persistence_result: PersistenceResult
    reload_result: WorkspaceLoadResult | None

    @property
    def status(self) -> str:
        return self.persistence_result.status

    @property
    def is_applied(self) -> bool:
        return self.persistence_result.is_applied

    @property
    def was_reloaded(self) -> bool:
        return self.reload_result is not None


class PresupuestoReloadAfterApplyError(
    RuntimeError
):
    def __init__(
        self,
        persistence_result: PersistenceResult,
    ):
        self.persistence_result = (
            persistence_result
        )

        super().__init__(
            "Los cambios fueron aplicados "
            "correctamente en BigQuery, "
            "pero no se pudo recargar el "
            "Workspace. No se debe volver "
            "a guardar el mismo cambio hasta "
            "recargar los datos."
        )


class PresupuestoSaveCoordinator:
    def __init__(
        self,
        persistence_service:
            PresupuestoPersistenceService,
        workspace_loader:
            PresupuestoWorkspaceLoader,
    ):
        self._persistence_service = (
            persistence_service
        )

        self._workspace_loader = (
            workspace_loader
        )

    def save_and_reload(
        self,
        *,
        actor: str,
        timestamp: datetime | None = None,
        batch_id_factory:
            Callable[[], str]
            = generate_batch_id,
    ) -> PresupuestoSaveOutcome:
        result = (
            self._persistence_service
            .save_changes(
                actor=actor,
                timestamp=timestamp,
                batch_id_factory=(
                    batch_id_factory
                ),
            )
        )

        if not result.is_applied:
            return PresupuestoSaveOutcome(
                persistence_result=result,
                reload_result=None,
            )

        try:
            reload_result = (
                self._workspace_loader
                .load()
            )

        except Exception as exc:
            raise (
                PresupuestoReloadAfterApplyError(
                    result
                )
            ) from exc

        return PresupuestoSaveOutcome(
            persistence_result=result,
            reload_result=reload_result,
        )
