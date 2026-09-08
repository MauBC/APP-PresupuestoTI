from dataclasses import dataclass
from time import perf_counter

from app.config.presupuesto_app_config import (
    ROW_ID_COLUMN,
)
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

    def load(
        self,
    ) -> WorkspaceLoadResult:
        total_start = perf_counter()

        fetch_start = perf_counter()

        rows = (
            self._repository
            .get_all_rows()
        )

        fetch_seconds = (
            perf_counter()
            - fetch_start
        )

        workspace_start = (
            perf_counter()
        )

        self._workspace.load(
            rows
        )

        workspace_seconds = (
            perf_counter()
            - workspace_start
        )

        total_seconds = (
            perf_counter()
            - total_start
        )

        return WorkspaceLoadResult(
            row_count=len(rows),
            fetch_seconds=fetch_seconds,
            workspace_seconds=(
                workspace_seconds
            ),
            total_seconds=total_seconds,
        )

    def reload_pending_rows(
        self,
    ) -> WorkspaceLoadResult:
        total_start = (
            perf_counter()
        )

        pending_changes = (
            self._workspace
            .get_pending_changes()
        )

        if not pending_changes:
            return WorkspaceLoadResult(
                row_count=0,
                fetch_seconds=0.0,
                workspace_seconds=0.0,
                total_seconds=(
                    perf_counter()
                    - total_start
                ),
            )

        row_ids = []

        for change in pending_changes:
            original = (
                self._workspace
                .get_original_row(
                    change.session_row_id
                )
            )

            row_id = str(
                original.get(
                    ROW_ID_COLUMN,
                    ""
                )
                or ""
            ).strip()

            if not row_id:
                raise RuntimeError(
                    "Una fila pendiente "
                    "no contiene row_id."
                )

            row_ids.append(
                row_id
            )

        fetch_start = (
            perf_counter()
        )

        rows = (
            self._repository
            .get_rows_by_ids(
                tuple(row_ids)
            )
        )

        fetch_seconds = (
            perf_counter()
            - fetch_start
        )

        workspace_start = (
            perf_counter()
        )

        row_count = (
            self._workspace
            .reconcile_persisted_rows(
                rows
            )
        )

        workspace_seconds = (
            perf_counter()
            - workspace_start
        )

        total_seconds = (
            perf_counter()
            - total_start
        )

        print(
            "[OPEX SAVE] "
            f"Reload filas          "
            f"{row_count:>7,}",
            flush=True,
        )

        print(
            "[OPEX SAVE] "
            f"Reload fetch          "
            f"{fetch_seconds:>7.2f} s",
            flush=True,
        )

        print(
            "[OPEX SAVE] "
            f"Reload workspace      "
            f"{workspace_seconds:>7.2f} s",
            flush=True,
        )

        return WorkspaceLoadResult(
            row_count=row_count,
            fetch_seconds=fetch_seconds,
            workspace_seconds=(
                workspace_seconds
            ),
            total_seconds=total_seconds,
        )
