from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
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
        persistence_result:
            PersistenceResult,
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


def _emit_timing(
    module_label: str,
    label: str,
    started: float,
):
    elapsed = (
        perf_counter()
        - started
    )

    print(
        f"[{module_label} SAVE] "
        f"{label:<22} "
        f"{elapsed:>7.2f} s",
        flush=True,
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

    @property
    def module_label(
        self,
    ) -> str:
        value = getattr(
            self._persistence_service,
            "module_label",
            "OPEX",
        )

        return str(
            value
            or "OPEX"
        )

    def _print_timing(
        self,
        label: str,
        started: float,
    ) -> None:
        _emit_timing(
            self.module_label,
            label,
            started,
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
        total_started = (
            perf_counter()
        )

        persistence_started = (
            perf_counter()
        )

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

        self._print_timing(
            "Servicio persistencia",
            persistence_started,
        )

        if not result.is_applied:
            self._print_timing(
                "TOTAL",
                total_started,
            )

            return PresupuestoSaveOutcome(
                persistence_result=result,
                reload_result=None,
            )

        reload_started = (
            perf_counter()
        )

        try:
            reload_pending = getattr(
                self._workspace_loader,
                "reload_pending_rows",
                None,
            )

            if reload_pending is None:
                reload_result = (
                    self._workspace_loader
                    .load()
                )
            else:
                reload_result = (
                    reload_pending()
                )

        except Exception as exc:
            self._print_timing(
                "Reload ERROR",
                reload_started,
            )

            self._print_timing(
                "TOTAL",
                total_started,
            )

            raise (
                PresupuestoReloadAfterApplyError(
                    result
                )
            ) from exc

        self._print_timing(
            "Reload selectivo",
            reload_started,
        )

        self._print_timing(
            "TOTAL",
            total_started,
        )

        return PresupuestoSaveOutcome(
            persistence_result=result,
            reload_result=reload_result,
        )
