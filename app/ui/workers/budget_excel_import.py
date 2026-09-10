
from PySide6.QtCore import (
    QThread,
    Signal,
)

from app.services.budget_excel_import_service import (
    BudgetExcelImportService,
)


class BudgetExcelImportThread(
    QThread
):
    loaded = Signal(
        object
    )

    failed = Signal(
        str
    )

    def __init__(
        self,
        *,
        module_config,
        file_path,
        actor,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._config = (
            module_config
        )

        self._file_path = str(
            file_path
        )

        self._actor = str(
            actor
        ).strip()

    def run(
        self,
    ):
        try:
            result = (
                BudgetExcelImportService(
                    self._config
                )
                .prepare(
                    self._file_path,
                    actor=(
                        self._actor
                    ),
                )
            )

        except Exception as exc:
            self.failed.emit(
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            return

        self.loaded.emit(
            result
        )
