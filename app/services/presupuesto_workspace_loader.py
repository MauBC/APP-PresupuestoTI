from dataclasses import dataclass
from time import perf_counter

from app.repositories.presupuesto_repository import (
    PresupuestoRepository,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)


@dataclass(frozen=True)
class WorkspaceLoadResult:
    row_count: int
    fetch_seconds: float
    workspace_seconds: float
    total_seconds: float


class PresupuestoWorkspaceLoader:
    def __init__(
        self,
        repository: PresupuestoRepository,
        workspace: PresupuestoWorkspace,
    ):
        self._repository = repository
        self._workspace = workspace

    def load(self) -> WorkspaceLoadResult:
        total_start = perf_counter()

        fetch_start = perf_counter()

        rows = self._repository.get_all_rows()

        fetch_seconds = (
            perf_counter() - fetch_start
        )

        workspace_start = perf_counter()

        self._workspace.load(rows)

        workspace_seconds = (
            perf_counter() - workspace_start
        )

        total_seconds = (
            perf_counter() - total_start
        )

        return WorkspaceLoadResult(
            row_count=len(rows),
            fetch_seconds=fetch_seconds,
            workspace_seconds=workspace_seconds,
            total_seconds=total_seconds,
        )