from dataclasses import dataclass
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
from app.services.presupuesto_history_service import (
    PresupuestoHistoryService,
)
from app.services.presupuesto_persistence_service import (
    PresupuestoPersistenceService,
)
from app.services.presupuesto_reversal_coordinator import (
    PresupuestoReversalCoordinator,
)
from app.services.presupuesto_save_coordinator import (
    PresupuestoReloadAfterApplyError,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_loader import (
    PresupuestoWorkspaceLoader,
)
from database.persistence.bigquery_repository import (
    BigQueryPersistenceRepository,
)


@dataclass(
    frozen=True,
    slots=True,
)
class PresupuestoReversalThreadFailure:
    message: str
    was_applied: bool
    source_batch_id: str
    batch_id: str | None = None


def build_reversal_coordinator(
    workspace: PresupuestoWorkspace,
) -> PresupuestoReversalCoordinator:
    bigquery = BigQueryService()

    module_config = (
        workspace.module_config
    )

    read_repository = (
        PresupuestoRepository(
            bigquery,
            module_config=(
                module_config
            ),
        )
    )

    persistence_repository = (
        BigQueryPersistenceRepository(
            bigquery.client,
            module_config=(
                module_config
            ),
        )
    )

    history_service = (
        PresupuestoHistoryService(
            persistence_repository
        )
    )

    persistence_service = (
        PresupuestoPersistenceService(
            workspace,
            persistence_repository,
        )
    )

    workspace_loader = (
        PresupuestoWorkspaceLoader(
            read_repository,
            workspace,
        )
    )

    return PresupuestoReversalCoordinator(
        workspace=workspace,
        history_service=(
            history_service
        ),
        read_repository=(
            read_repository
        ),
        persistence_service=(
            persistence_service
        ),
        workspace_loader=(
            workspace_loader
        ),
    )


class PresupuestoReversalThread(
    QThread
):
    completed = Signal(object)
    failed = Signal(object)

    def __init__(
        self,
        workspace:
            PresupuestoWorkspace,
        batch,
        actor: str,
        parent=None,
        *,
        coordinator_factory:
            Callable[
                [PresupuestoWorkspace],
                PresupuestoReversalCoordinator,
            ]
            = build_reversal_coordinator,
    ):
        super().__init__(
            parent
        )

        actor_value = str(
            actor
            if actor is not None
            else ""
        ).strip()

        if not actor_value:
            raise ValueError(
                "actor no puede estar vacio."
            )

        batch_id = str(
            getattr(
                batch,
                "batch_id",
                "",
            )
            or ""
        ).strip()

        if not batch_id:
            raise ValueError(
                "batch no contiene batch_id."
            )

        self._workspace = workspace
        self._batch = batch
        self._actor = actor_value

        self._coordinator_factory = (
            coordinator_factory
        )

    def run(
        self,
    ):
        source_batch_id = (
            self._batch.batch_id
        )

        try:
            coordinator = (
                self._coordinator_factory(
                    self._workspace
                )
            )

            outcome = (
                coordinator
                .revert_and_reload(
                    self._batch,
                    actor=self._actor,
                )
            )

        except (
            PresupuestoReloadAfterApplyError
        ) as exc:
            self.failed.emit(
                PresupuestoReversalThreadFailure(
                    message=str(exc),
                    was_applied=True,
                    source_batch_id=(
                        source_batch_id
                    ),
                    batch_id=(
                        exc
                        .persistence_result
                        .batch_id
                    ),
                )
            )

            return

        except Exception as exc:
            self.failed.emit(
                PresupuestoReversalThreadFailure(
                    message=(
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                    was_applied=False,
                    source_batch_id=(
                        source_batch_id
                    ),
                    batch_id=None,
                )
            )

            return

        self.completed.emit(
            outcome
        )
