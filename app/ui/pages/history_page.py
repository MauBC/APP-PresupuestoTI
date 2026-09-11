from datetime import datetime

from PySide6.QtCore import (
    Qt,
    Signal,
)
from PySide6.QtGui import QColor
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
    "TIPO",
    "FILAS",
    "CAMPOS",
    "BATCH ID",
    "RELACION",
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
        return str(value)

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


def history_operation_code(
    batch,
) -> str:
    if batch is None:
        return ""

    if getattr(
        batch,
        "reverted_batch_id",
        None,
    ):
        return "REVERSAL"

    if getattr(
        batch,
        "reversal_batch_id",
        None,
    ):
        return "REVERTED"

    return "CHANGE"


def format_history_operation(
    batch,
) -> str:
    labels = {
        "CHANGE": "CAMBIO",
        "REVERTED": "REVERTIDO",
        "REVERSAL": "REVERSION",
    }

    return labels.get(
        history_operation_code(
            batch
        ),
        "",
    )


def format_history_relation(
    batch,
) -> str:
    if batch is None:
        return ""

    source = getattr(
        batch,
        "reverted_batch_id",
        None,
    )

    if source:
        return (
            "Revierte: "
            + str(source)
        )

    reversal = getattr(
        batch,
        "reversal_batch_id",
        None,
    )

    if reversal:
        return (
            "Revertido por: "
            + str(reversal)
        )

    return ""


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

    if getattr(
        batch,
        "reverted_batch_id",
        None,
    ):
        return False

    if getattr(
        batch,
        "reversal_batch_id",
        None,
    ):
        return False

    # Compatibilidad con objetos antiguos/tests
    # que todavia no exponen reversal_batch_id.
    applied_reverted_sources = {
        getattr(
            item,
            "reverted_batch_id",
            None,
        )
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
        getattr(
            batch,
            "batch_id",
            None,
        )
        not in applied_reverted_sources
    )


class HistoryPage(QWidget):
    reversal_requested = Signal(
        object
    )

    PAGE_LIMIT = 500

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
        return bool(
            (
                self._worker is not None
                and self._worker.isRunning()
            )
            or
            (
                self._detail_worker
                is not None
                and self._detail_worker
                .isRunning()
            )
        )

    def _setup_ui(
        self,
    ):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            32,
            28,
            32,
            32,
        )

        layout.setSpacing(14)

        title = QLabel("Historial")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Consulta operaciones confirmadas "
            "en BigQuery, su auditoria y las "
            "relaciones entre cambios y reversiones."
        )

        subtitle.setObjectName(
            "pageSubtitle"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()

        self.status_combo = QComboBox()

        self.status_combo.addItem(
            "Aplicados",
            "APPLIED",
        )

        self.status_combo.addItem(
            "Todos los estados",
            None,
        )

        self.status_combo.addItem(
            "Conflictos",
            "CONFLICT",
        )

        self.status_combo.addItem(
            "Errores",
            "FAILED",
        )

        self.status_combo.addItem(
            "Pendientes",
            "PENDING",
        )

        self.type_combo = QComboBox()

        self.type_combo.addItem(
            "Todos los tipos",
            "ALL",
        )

        self.type_combo.addItem(
            "Cambios",
            "CHANGE",
        )

        self.type_combo.addItem(
            "Revertidos",
            "REVERTED",
        )

        self.type_combo.addItem(
            "Reversiones",
            "REVERSAL",
        )

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "Buscar usuario, batch, relacion..."
        )

        self.detail_button = QPushButton(
            "Ver detalle"
        )

        self.detail_button.setEnabled(
            False
        )

        self.reversal_button = QPushButton(
            "Revertir"
        )

        self.reversal_button.setObjectName(
            "dangerButton"
        )

        self.reversal_button.setEnabled(
            False
        )

        self.refresh_button = QPushButton(
            "Actualizar historial"
        )

        self.refresh_button.setObjectName(
            "primaryButton"
        )

        toolbar.addWidget(
            QLabel("Estado:")
        )

        toolbar.addWidget(
            self.status_combo
        )

        toolbar.addWidget(
            QLabel("Tipo:")
        )

        toolbar.addWidget(
            self.type_combo
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

        layout.addLayout(toolbar)

        self.summary_label = QLabel(
            "Historial sin cargar"
        )

        self.summary_label.setObjectName(
            "analysisSummary"
        )

        layout.addWidget(
            self.summary_label
        )

        self.table = QTableWidget()

        self.table.setColumnCount(
            len(HISTORY_COLUMNS)
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

        self.table.verticalHeader().setVisible(
            False
        )

        self.table.verticalHeader().setDefaultSectionSize(
            30
        )

        header = (
            self.table.horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView
            .ResizeMode
            .Interactive
        )

        widths = (
            155,
            180,
            105,
            115,
            75,
            80,
            275,
            330,
        )

        for index, width in enumerate(
            widths
        ):
            header.resizeSection(
                index,
                width,
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

        self.type_combo.currentIndexChanged.connect(
            self._apply_filters
        )

        self.search_input.textChanged.connect(
            self._apply_filters
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

        self._worker = self._worker_factory(
            self._module_config,
            status=(
                self.status_combo.currentData()
            ),
            limit=self.PAGE_LIMIT,
            offset=0,
            parent=self,
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

        changes = sum(
            history_operation_code(batch)
            == "CHANGE"
            for batch in self._batches
        )

        reverted = sum(
            history_operation_code(batch)
            == "REVERTED"
            for batch in self._batches
        )

        reversals = sum(
            history_operation_code(batch)
            == "REVERSAL"
            for batch in self._batches
        )

        self.summary_label.setText(
            f"{len(self._batches):,} operaciones"
            f" | Modulo: "
            f"{self._module_config.label}"
            f" | Cambios: {changes:,}"
            f" | Revertidos: {reverted:,}"
            f" | Reversiones: {reversals:,}"
        )

        self._apply_filters()

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
            len(self._batches)
        )

        type_colors = {
            "CHANGE": "#344054",
            "REVERTED": "#92400E",
            "REVERSAL": "#067647",
        }

        type_backgrounds = {
            "CHANGE": "#F2F4F7",
            "REVERTED": "#FFF4E5",
            "REVERSAL": "#ECFDF3",
        }

        for row_index, batch in enumerate(
            self._batches
        ):
            operation_code = (
                history_operation_code(
                    batch
                )
            )

            values = (
                format_history_datetime(
                    batch.created_at
                ),
                batch.actor,
                format_history_status(
                    batch.status
                ),
                format_history_operation(
                    batch
                ),
                str(batch.row_count),
                str(batch.field_count),
                batch.batch_id,
                format_history_relation(
                    batch
                ),
            )

            for column_index, value in enumerate(
                values
            ):
                item = QTableWidgetItem(
                    str(value)
                )

                item.setData(
                    Qt.ItemDataRole.UserRole,
                    operation_code,
                )

                if column_index == 3:
                    item.setForeground(
                        QColor(
                            type_colors.get(
                                operation_code,
                                "#344054",
                            )
                        )
                    )

                    item.setBackground(
                        QColor(
                            type_backgrounds.get(
                                operation_code,
                                "#F2F4F7",
                            )
                        )
                    )

                self.table.setItem(
                    row_index,
                    column_index,
                    item,
                )

        self.table.setSortingEnabled(
            True
        )

    def _apply_filters(
        self,
        *_,
    ):
        query = (
            self.search_input
            .text()
            .strip()
            .casefold()
        )

        selected_type = (
            self.type_combo
            .currentData()
        )

        visible_count = 0

        for row_index in range(
            self.table.rowCount()
        ):
            type_item = self.table.item(
                row_index,
                3,
            )

            operation_code = (
                type_item.data(
                    Qt.ItemDataRole.UserRole
                )
                if type_item is not None
                else ""
            )

            type_matches = (
                selected_type == "ALL"
                or operation_code
                == selected_type
            )

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

            search_matches = (
                not query
                or query in blob
            )

            visible = (
                type_matches
                and search_matches
            )

            self.table.setRowHidden(
                row_index,
                not visible,
            )

            if visible:
                visible_count += 1

        self.status_label.setText(
            f"Mostrando "
            f"{visible_count:,} de "
            f"{len(self._batches):,} "
            "operaciones cargadas."
        )

    def _update_detail_button(
        self,
    ):
        batch = self.selected_batch()

        detail_busy = (
            self._detail_worker
            is not None
            and self._detail_worker
            .isRunning()
        )

        self.detail_button.setEnabled(
            batch is not None
            and not detail_busy
        )

        reversal_enabled = (
            can_revert_history_batch(
                batch,
                self._batches,
            )
            and not detail_busy
        )

        self.reversal_button.setEnabled(
            reversal_enabled
        )

        if batch is None:
            tooltip = (
                "Selecciona una operacion."
            )

        elif (
            str(batch.status)
            .strip()
            .upper()
            != "APPLIED"
        ):
            tooltip = (
                "Solo los batches APLICADOS "
                "pueden revertirse."
            )

        elif getattr(
            batch,
            "reverted_batch_id",
            None,
        ):
            tooltip = (
                "Este batch ya es una reversion."
            )

        elif getattr(
            batch,
            "reversal_batch_id",
            None,
        ):
            tooltip = (
                "Este batch ya fue revertido por "
                f"{batch.reversal_batch_id}."
            )

        elif not reversal_enabled:
            tooltip = (
                "Este batch ya tiene una "
                "reversion aplicada."
            )

        else:
            tooltip = (
                "Crea un nuevo batch compensatorio "
                "que restaura los valores anteriores."
            )

        self.reversal_button.setToolTip(
            tooltip
        )

    def _request_selected_reversal(
        self,
    ):
        batch = self.selected_batch()

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
            self._detail_worker is not None
            and self._detail_worker.isRunning()
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

        self._apply_filters()
        self._update_detail_button()

    def selected_batch(
        self,
    ):
        row = self.table.currentRow()

        if row < 0:
            return None

        batch_item = self.table.item(
            row,
            6,
        )

        if batch_item is None:
            return None

        batch_id = batch_item.text()

        return next(
            (
                batch
                for batch in self._batches
                if batch.batch_id
                == batch_id
            ),
            None,
        )
