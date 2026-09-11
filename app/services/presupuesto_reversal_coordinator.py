from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Callable

from app.config.settings import (
    settings,
)
from app.models.budget_history import (
    BudgetHistoryBatch,
    BudgetHistoryDetail,
)
from app.models.budget_reversal import (
    BudgetReversalProposal,
)
from app.services.presupuesto_reversal_service import (
    PresupuestoReversalService,
)
from app.services.presupuesto_save_coordinator import (
    PresupuestoReloadAfterApplyError,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
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


class PresupuestoReversalCoordinatorError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class PresupuestoReversalOutcome:
    source_batch: BudgetHistoryBatch
    detail: BudgetHistoryDetail
    proposal: BudgetReversalProposal
    persistence_result: PersistenceResult
    reload_result: WorkspaceLoadResult | None

    @property
    def status(
        self,
    ) -> str:
        return (
            self.persistence_result
            .status
        )

    @property
    def is_applied(
        self,
    ) -> bool:
        return (
            self.persistence_result
            .is_applied
        )

    @property
    def was_reloaded(
        self,
    ) -> bool:
        return (
            self.reload_result
            is not None
        )


def _print_timing(
    label: str,
    started: float,
):
    elapsed = (
        perf_counter()
        - started
    )

    print(
        "[BUDGET REVERT] "
        f"{label:<24} "
        f"{elapsed:>7.2f} s",
        flush=True,
    )


class PresupuestoReversalCoordinator:
    def __init__(
        self,
        *,
        workspace:
            PresupuestoWorkspace,
        history_service,
        read_repository,
        persistence_service,
        workspace_loader:
            PresupuestoWorkspaceLoader,
        reversal_service=(
            PresupuestoReversalService
        ),
        app_version: str | None = None,
    ):
        if workspace is None:
            raise ValueError(
                "workspace es requerido."
            )

        if history_service is None:
            raise ValueError(
                "history_service es requerido."
            )

        if read_repository is None:
            raise ValueError(
                "read_repository es requerido."
            )

        if persistence_service is None:
            raise ValueError(
                "persistence_service es requerido."
            )

        if workspace_loader is None:
            raise ValueError(
                "workspace_loader es requerido."
            )

        if reversal_service is None:
            raise ValueError(
                "reversal_service es requerido."
            )

        self._workspace = workspace
        self._history_service = (
            history_service
        )
        self._read_repository = (
            read_repository
        )
        self._persistence_service = (
            persistence_service
        )
        self._workspace_loader = (
            workspace_loader
        )
        self._reversal_service = (
            reversal_service
        )

        if app_version is None:
            app_version = (
                settings.APP_VERSION
            )

        app_version_value = str(
            app_version
            if app_version is not None
            else ""
        ).strip()

        self._app_version = (
            app_version_value
            or None
        )

    def revert_and_reload(
        self,
        batch: BudgetHistoryBatch,
        *,
        actor: str,
        timestamp: datetime | None = None,
        batch_id_factory:
            Callable[[], str]
            = generate_batch_id,
    ) -> PresupuestoReversalOutcome:
        if not isinstance(
            batch,
            BudgetHistoryBatch,
        ):
            raise TypeError(
                "batch debe ser "
                "BudgetHistoryBatch."
            )

        self._ensure_persistence_enabled()

        total_started = (
            perf_counter()
        )

        self._ensure_workspace_clean()

        active_module = (
            self._active_module()
        )

        batch_module = (
            batch.budget_module
            .strip()
            .upper()
        )

        if (
            batch_module
            != active_module
        ):
            raise (
                PresupuestoReversalCoordinatorError(
                    "El batch pertenece al "
                    f"modulo {batch_module}, "
                    "pero el Workspace activo "
                    f"es {active_module}."
                )
            )

        detail_started = (
            perf_counter()
        )

        detail = (
            self._history_service
            .get_batch_detail(
                batch
            )
        )

        _print_timing(
            "Detalle historial",
            detail_started,
        )

        read_started = (
            perf_counter()
        )

        current_rows = (
            self._read_repository
            .get_rows_by_ids(
                detail.row_ids
            )
        )

        _print_timing(
            "Lectura filas actuales",
            read_started,
        )

        proposal_started = (
            perf_counter()
        )

        proposal = (
            self._reversal_service
            .build_proposal(
                detail,
                current_rows,
                actor=actor,
                app_version=(
                    self._app_version
                ),
                timestamp=timestamp,
                batch_id_factory=(
                    batch_id_factory
                ),
                expected_module=(
                    active_module
                ),
            )
        )

        _print_timing(
            "Propuesta reversion",
            proposal_started,
        )

        # Segunda barrera:
        # no permitir que un cambio local
        # aparezca entre la lectura y
        # la persistencia.
        self._ensure_workspace_clean()

        persistence_started = (
            perf_counter()
        )

        result = (
            self._persistence_service
            .persist_batch(
                proposal.batch
            )
        )

        _print_timing(
            "Persistencia",
            persistence_started,
        )

        if not result.is_applied:
            _print_timing(
                "TOTAL",
                total_started,
            )

            return PresupuestoReversalOutcome(
                source_batch=batch,
                detail=detail,
                proposal=proposal,
                persistence_result=result,
                reload_result=None,
            )

        reload_started = (
            perf_counter()
        )

        try:
            reload_result = (
                self._workspace_loader
                .reload_rows_by_ids(
                    proposal.row_ids
                )
            )

        except Exception as exc:
            _print_timing(
                "Reload ERROR",
                reload_started,
            )

            _print_timing(
                "TOTAL",
                total_started,
            )

            raise (
                PresupuestoReloadAfterApplyError(
                    result
                )
            ) from exc

        _print_timing(
            "Reload selectivo",
            reload_started,
        )

        _print_timing(
            "TOTAL",
            total_started,
        )

        return PresupuestoReversalOutcome(
            source_batch=batch,
            detail=detail,
            proposal=proposal,
            persistence_result=result,
            reload_result=(
                reload_result
            ),
        )

    def _ensure_persistence_enabled(
        self,
    ) -> None:
        module_config = (
            self._workspace
            .module_config
        )

        capabilities = getattr(
            module_config,
            "capabilities",
            None,
        )

        persistence_enabled = getattr(
            capabilities,
            "persistence",
            True,
        )

        if not persistence_enabled:
            raise (
                PresupuestoReversalCoordinatorError(
                    "El modulo activo no permite "
                    "operaciones de persistencia "
                    "ni reversion."
                )
            )

    def _ensure_workspace_clean(
        self,
    ) -> None:
        if self._workspace.has_changes:
            raise (
                PresupuestoReversalCoordinatorError(
                    "No se puede revertir un "
                    "batch historico mientras "
                    "existen cambios locales "
                    "pendientes."
                )
            )

    def _active_module(
        self,
    ) -> str:
        module = (
            self._workspace
            .module_config
            .module
        )

        value = getattr(
            module,
            "value",
            module,
        )

        text = str(
            value
        ).strip().upper()

        if not text:
            raise (
                PresupuestoReversalCoordinatorError(
                    "No se pudo determinar "
                    "el modulo activo."
                )
            )

        return text
