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
from app.services.presupuesto_persistence_service import (
    PresupuestoPersistenceService,
)
from app.services.presupuesto_save_coordinator import (
    PresupuestoReloadAfterApplyError,
    PresupuestoSaveCoordinator,
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


@dataclass(frozen=True)
class PresupuestoSaveThreadFailure:
    message: str
    was_applied: bool
    batch_id: str | None = None


def build_save_coordinator(
    workspace: PresupuestoWorkspace,
) -> PresupuestoSaveCoordinator:
    bigquery = BigQueryService()

    read_repository = (
        PresupuestoRepository(
            bigquery,
            module_config=(
                workspace.module_config
            ),
        )
    )

    persistence_repository = (
        BigQueryPersistenceRepository(
            bigquery.client,
            module_config=(
                workspace.module_config
            ),
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

    return PresupuestoSaveCoordinator(
        persistence_service,
        workspace_loader,
    )


class PresupuestoSaveThread(
    QThread
):
    completed = Signal(
        object
    )

    failed = Signal(
        object
    )

    def __init__(
        self,
        workspace:
            PresupuestoWorkspace,
        actor: str,
        parent=None,
        *,
        coordinator_factory:
            Callable[
                [PresupuestoWorkspace],
                PresupuestoSaveCoordinator,
            ]
            = build_save_coordinator,
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

        self._workspace = workspace
        self._actor = actor_value

        self._coordinator_factory = (
            coordinator_factory
        )

    def run(
        self,
    ):
        try:
            coordinator = (
                self._coordinator_factory(
                    self._workspace
                )
            )

            outcome = (
                coordinator
                .save_and_reload(
                    actor=self._actor
                )
            )

        except (
            PresupuestoReloadAfterApplyError
        ) as exc:
            self.failed.emit(
                PresupuestoSaveThreadFailure(
                    message=str(
                        exc
                    ),
                    was_applied=True,
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
                PresupuestoSaveThreadFailure(
                    message=str(
                        exc
                    ),
                    was_applied=False,
                    batch_id=None,
                )
            )

            return

        self.completed.emit(
            outcome
        )
