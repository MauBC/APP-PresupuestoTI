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
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_loader import (
    PresupuestoWorkspaceLoader,
)


class WorkspaceLoadThread(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        workspace: PresupuestoWorkspace,
        parent=None,
    ):
        super().__init__(parent)

        self._workspace = workspace

    def run(self):
        try:
            bigquery = BigQueryService()

            repository = PresupuestoRepository(
                bigquery,
                module_config=(
                    self._workspace
                    .module_config
                ),
            )

            loader = PresupuestoWorkspaceLoader(
                repository,
                self._workspace,
            )

            result = loader.load()

            self.loaded.emit(result)

        except Exception as exc:
            self.failed.emit(
                f"{type(exc).__name__}: {exc}"
            )