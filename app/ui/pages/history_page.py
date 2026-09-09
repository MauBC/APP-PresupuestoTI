from datetime import datetime

from PySide6.QtCore import (
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.dialogs.history_detail_dialog import (
    HistoryDetailDialog,
)
from app.ui.workers.history_detail_loader import (
    HistoryDetailLoadThread,
)
from app.ui.workers.history_loader import (
    HistoryLoadThread,
)


HISTORY_COLUMNS = (
    "FECHA",
    "USUARIO",
    "ESTADO",
    "FILAS",
    "CAMPOS",
    "BATCH ID",
    "VERSION APP",
    "REVERSION DE",
)


def format_history_datetime(
    value,
) -> str:
    if value is None:
        return ""

    if not isinstance(
        value,
        datetime,
    ):
        return str(
            value
        )

    if (
        value.tzinfo is not None
        and value.utcoffset() is not None
    ):
        value = value.astimezone()

    return value.strftime(
        "%d/%m/%Y %H:%M:%S"
    )


def format_history_status(
    status,
) -> str:
    value = str(
        status
        if status is not None
        else ""
    ).strip().upper()

    labels = {
        "APPLIED": "APLICADO",
        "CONFLICT": "CONFLICTO",
        "FAILED": "ERROR",
        "PENDING": "PENDIENTE",
    }

    return labels.get(
        value,
        value,
    )


def can_revert_history_batch(
    batch,
    batches=(),
) -> bool:
    if batch is None:
        return False

    status = str(
        getattr(
            batch,
            "status",
            "",
        )
        or ""
    ).strip().upper()

    if status != "APPLIED":
        return False

    if (
        getattr(
            batch,
            "reverted_batch_id",
            None,
        )
        is not None
    ):
        return False

    applied_reverted_sources = {
        item.reverted_batch_id
        for item in batches
        if (
            str(
                getattr(
                    item,
                    "status",
                    "",
                )
                or ""
            ).strip().upper()
            == "APPLIED"
            and getattr(
                item,
                "reverted_batch_id",
                None,
            )
        )
    }

    return (
        batch.batch_id
        not in applied_reverted_sources
    )


class HistoryPage(QWidget):
    reversal_requested = Signal(
        object
    )

    def __init__(
        self,
        *,
        module_config,
        worker_factory=(
            HistoryLoadThread
        ),
        detail_worker_factory=(
            HistoryDetailLoadThread
        ),
        detail_dialog_factory=(
            HistoryDetailDialog
        ),
    ):
        super().__init__()

        self._module_config = (
            module_config
        )

        self._worker_factory = (
            worker_factory
        )

        self._detail_worker_factory = (
            detail_worker_factory
        )

        self._detail_dialog_factory = (
            detail_dialog_factory
        )

        self._worker = None
        self._detail_worker = None
        self._loaded_once = False

        self._batches = ()

        self._setup_ui()

    @property
    def is_busy(
        self,
    ) -> bool:
        worker_busy = (
            self._worker is not None
            and self._worker.isRunning()
        )

        detail_busy = (
            self._detail_worker
            is not None
            and self._detail_worker
            .isRunning()
        )

        return bool(
            worker_busy
            or detail_busy
        )

    def _setup_ui(
        self,
    ):
        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            32,
            28,
            32,
            32,
        )

        layout.setSpacing(
            14
        )

        title = QLabel(
            "Historial"
        )

        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "Consulta operaciones aplicadas "
            "en BigQuery. El historial es "
            "inmutable y se muestra por modulo."
        )

        subtitle.setObjectName(
            "pageSubtitle"
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        toolbar = QHBoxLayout()

        self.status_combo = (
            QComboBox()
        )

        self.status_combo.addItem(
            "Aplicados",
            "APPLIED",
        )

        self.status_combo.addItem(
            "Todos los estados",
            None,
        )

        self.search_input = (
            QLineEdit()
        )

        self.search_input.setPlaceholderText(
            "Buscar usuario, batch, estado..."
        )

        self.detail_button = (
            QPushButton(
                "Ver detalle"
            )
        )

        self.detail_button.setEnabled(
            False
        )

        self.reversal_button = (
            QPushButton(
                "Revertir"
            )
        )

        self.reversal_button.setObjectName(
            "dangerButton"
        )

        self.reversal_button.setEnabled(
            False
        )

        self.reversal_button.setToolTip(
            "Crea un nuevo batch que restaura "
            "los valores anteriores."
        )

        self.refresh_button = (
            QPushButton(
                "Actualizar historial"
            )
        )

        self.refresh_button.setObjectName(
            "primaryButton"
        )

        toolbar.addWidget(
            QLabel(
                "Estado:"
            )
        )

        toolbar.addWidget(
            self.status_combo
        )

        toolbar.addWidget(
            self.search_input,
            1,
        )

        toolbar.addWidget(
            self.detail_button
        )

        toolbar.addWidget(
            self.reversal_button
        )

        toolbar.addWidget(
            self.refresh_button
        )

        layout.addLayout(
            toolbar
        )

        self.summary_label = QLabel(
            "Historial sin cargar"
        )

        self.summary_label.setObjectName(
            "analysisSummary"
        )

        layout.addWidget(
            self.summary_label
        )

        self.table = (
            QTableWidget()
        )

        self.table.setColumnCount(
            len(
                HISTORY_COLUMNS
            )
        )

        self.table.setHorizontalHeaderLabels(
            HISTORY_COLUMNS
        )

        self.table.setAlternatingRowColors(
            True
        )

        self.table.setEditTriggers(
            QAbstractItemView
            .EditTrigger
            .NoEditTriggers
        )

        self.table.setSelectionBehavior(
            QAbstractItemView
            .SelectionBehavior
            .SelectRows
        )

        self.table.setSelectionMode(
            QAbstractItemView
            .SelectionMode
            .SingleSelection
        )

        self.table.setSortingEnabled(
            False
        )

        self.table.verticalHeader().setVisible(
            False
        )

        self.table.verticalHeader().setDefaultSectionSize(
            30
        )

        header = (
            self.table
            .horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView
            .ResizeMode
            .Interactive
        )

        header.setDefaultSectionSize(
            130
        )

        header.resizeSection(
            0,
            155,
        )

        header.resizeSection(
            1,
            180,
        )

        header.resizeSection(
            2,
            100,
        )

        header.resizeSection(
            3,
            80,
        )

        header.resizeSection(
            4,
            80,
        )

        header.resizeSection(
            5,
            280,
        )

        header.resizeSection(
            6,
            100,
        )

        header.resizeSection(
            7,
            280,
        )

        layout.addWidget(
            self.table,
            1,
        )

        self.status_label = QLabel(
            "Abre Historial para consultar "
            "los cambios guardados."
        )

        self.status_label.setObjectName(
            "tableStatus"
        )

        layout.addWidget(
            self.status_label
        )

        self.refresh_button.clicked.connect(
            self.refresh
        )

        self.status_combo.currentIndexChanged.connect(
            self._reload_for_status
        )

        self.search_input.textChanged.connect(
            self._apply_search
        )

        self.table.itemSelectionChanged.connect(
            self._update_detail_button
        )

        self.table.itemDoubleClicked.connect(
            self._open_selected_detail
        )

        self.detail_button.clicked.connect(
            self._open_selected_detail
        )

        self.reversal_button.clicked.connect(
            self._request_selected_reversal
        )

    def ensure_loaded(
        self,
    ):
        if not self._loaded_once:
            self.refresh()

    def invalidate(
        self,
    ):
        self._loaded_once = False

    def refresh(
        self,
    ):
        if (
            self._worker is not None
            and self._worker.isRunning()
        ):
            return

        self.refresh_button.setEnabled(
            False
        )

        self.status_combo.setEnabled(
            False
        )

        self.status_label.setText(
            "Consultando historial en BigQuery..."
        )

        status = (
            self.status_combo
            .currentData()
        )

        self._worker = (
            self._worker_factory(
                self._module_config,
                status=status,
                limit=200,
                offset=0,
                parent=self,
            )
        )

        self._worker.loaded.connect(
            self._on_loaded
        )

        self._worker.failed.connect(
            self._on_failed
        )

        self._worker.finished.connect(
            self._on_finished
        )

        self._worker.start()

    def _reload_for_status(
        self,
    ):
        if self._loaded_once:
            self.refresh()

    def _on_loaded(
        self,
        batches,
    ):
        self._batches = tuple(
            batches
        )

        self._populate_table()

        self.table.clearSelection()

        self.detail_button.setEnabled(
            False
        )

        self.reversal_button.setEnabled(
            False
        )

        self._loaded_once = True

        module_label = (
            self._module_config
            .label
        )

        self.summary_label.setText(
            f"{len(self._batches):,} "
            f"operaciones | "
            f"Modulo: {module_label}"
        )

        self.status_label.setText(
            "Historial actualizado."
        )

    def _on_failed(
        self,
        message,
    ):
        self.status_label.setText(
            "No se pudo cargar el historial: "
            + str(message)
        )

    def _on_finished(
        self,
    ):
        self.refresh_button.setEnabled(
            True
        )

        self.status_combo.setEnabled(
            True
        )

        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

        self._update_detail_button()

    def _populate_table(
        self,
    ):
        self.table.setSortingEnabled(
            False
        )

        self.table.setRowCount(
            len(
                self._batches
            )
        )

        for row_index, batch in enumerate(
            self._batches
        ):
            values = (
                format_history_datetime(
                    batch.created_at
                ),
                batch.actor,
                format_history_status(
                    batch.status
                ),
                str(
                    batch.row_count
                ),
                str(
                    batch.field_count
                ),
                batch.batch_id,
                (
                    batch.app_version
                    or ""
                ),
                (
                    batch.reverted_batch_id
                    or ""
                ),
            )

            for (
                column_index,
                value,
            ) in enumerate(values):
                item = (
                    QTableWidgetItem(
                        value
                    )
                )

                item.setData(
                    Qt.ItemDataRole
                    .UserRole,
                    value,
                )

                self.table.setItem(
                    row_index,
                    column_index,
                    item,
                )

        self.table.setSortingEnabled(
            True
        )

        self._apply_search(
            self.search_input.text()
        )

    def _apply_search(
        self,
        text,
    ):
        query = str(
            text
            if text is not None
            else ""
        ).strip().casefold()

        for row_index in range(
            self.table.rowCount()
        ):
            values = []

            for column_index in range(
                self.table.columnCount()
            ):
                item = self.table.item(
                    row_index,
                    column_index,
                )

                if item is not None:
                    values.append(
                        item.text()
                    )

            blob = " ".join(
                values
            ).casefold()

            self.table.setRowHidden(
                row_index,
                bool(
                    query
                    and query not in blob
                ),
            )

    def _update_detail_button(
        self,
    ):
        batch = (
            self.selected_batch()
        )

        detail_enabled = (
            batch is not None
        )

        detail_busy = (
            self._detail_worker
            is not None
            and self._detail_worker
            .isRunning()
        )

        if detail_busy:
            detail_enabled = False

        self.detail_button.setEnabled(
            detail_enabled
        )

        reversal_enabled = (
            can_revert_history_batch(
                batch,
                self._batches,
            )
        )

        if detail_busy:
            reversal_enabled = False

        self.reversal_button.setEnabled(
            reversal_enabled
        )

        if batch is None:
            tooltip = (
                "Selecciona un batch aplicado."
            )

        elif (
            str(batch.status)
            .strip()
            .upper()
            != "APPLIED"
        ):
            tooltip = (
                "Solo los batches APPLIED "
                "pueden revertirse."
            )

        elif batch.reverted_batch_id:
            tooltip = (
                "Este batch ya corresponde "
                "a una reversi\u00f3n."
            )

        elif not reversal_enabled:
            tooltip = (
                "Este batch ya tiene una "
                "reversi\u00f3n aplicada."
            )

        else:
            tooltip = (
                "Crea un nuevo batch que "
                "restaura los valores anteriores."
            )

        self.reversal_button.setToolTip(
            tooltip
        )

    def _request_selected_reversal(
        self,
    ):
        batch = (
            self.selected_batch()
        )

        if not can_revert_history_batch(
            batch,
            self._batches,
        ):
            return

        self.reversal_requested.emit(
            batch
        )

    def _open_selected_detail(
        self,
        *_,
    ):
        batch = self.selected_batch()

        if batch is None:
            return

        if (
            self._detail_worker
            is not None
            and self._detail_worker
            .isRunning()
        ):
            return

        self.detail_button.setEnabled(
            False
        )

        self.status_label.setText(
            "Consultando detalle del batch "
            f"{batch.batch_id}..."
        )

        self._detail_worker = (
            self._detail_worker_factory(
                self._module_config,
                batch,
                parent=self,
            )
        )

        self._detail_worker.loaded.connect(
            self._on_detail_loaded
        )

        self._detail_worker.failed.connect(
            self._on_detail_failed
        )

        self._detail_worker.finished.connect(
            self._on_detail_finished
        )

        self._detail_worker.start()

    def _on_detail_loaded(
        self,
        detail,
    ):
        self.status_label.setText(
            f"Detalle cargado: "
            f"{detail.audit_count:,} cambios."
        )

        dialog = (
            self._detail_dialog_factory(
                detail,
                self,
            )
        )

        dialog.exec()

    def _on_detail_failed(
        self,
        message,
    ):
        self.status_label.setText(
            "No se pudo cargar el detalle: "
            + str(message)
        )

    def _on_detail_finished(
        self,
    ):
        if self._detail_worker is not None:
            self._detail_worker.deleteLater()
            self._detail_worker = None

        self._update_detail_button()

    def selected_batch(
        self,
    ):
        row = (
            self.table
            .currentRow()
        )

        if row < 0:
            return None

        batch_item = self.table.item(
            row,
            5,
        )

        if batch_item is None:
            return None

        batch_id = (
            batch_item
            .text()
        )

        return next(
            (
                batch
                for batch
                in self._batches
                if (
                    batch.batch_id
                    == batch_id
                )
            ),
            None,
        )
