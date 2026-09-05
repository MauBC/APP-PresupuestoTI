from decimal import Decimal

from PySide6.QtCore import (
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.models.presupuesto_table_model import (
    PresupuestoTableModel,
)


class PresupuestoPage(QWidget):
    workspace_changed = Signal()

    MAX_CHANGE_PREVIEW = 5000

    def __init__(
        self,
        *,
        workspace,
        analysis_service,
    ):
        super().__init__()

        self._workspace = workspace

        self._analysis_service = (
            analysis_service
        )

        self._page_index = 0
        self._page_size = 250
        self._total_rows = 0

        self._workspace_ready = False
        self._loaded_once = False

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            32,
            28,
            32,
            32,
        )

        layout.setSpacing(14)

        title = QLabel(
            "Presupuesto"
        )

        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "Simula modificaciones en USD. "
            "Todos los cambios permanecen "
            "locales hasta que exista un "
            "proceso de guardado aprobado."
        )

        subtitle.setObjectName(
            "pageSubtitle"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "Buscar en la pagina actual..."
        )

        self.page_size_combo = QComboBox()

        self.page_size_combo.addItems(
            [
                "100",
                "250",
                "500",
                "1000",
            ]
        )

        self.page_size_combo.setCurrentText(
            "250"
        )

        self.refresh_button = QPushButton(
            "Actualizar vista"
        )

        self.refresh_button.setEnabled(
            False
        )

        toolbar.addWidget(
            self.search_input,
            1,
        )

        toolbar.addWidget(
            QLabel("Filas:")
        )

        toolbar.addWidget(
            self.page_size_combo
        )

        toolbar.addWidget(
            self.refresh_button
        )

        layout.addLayout(
            toolbar
        )

        changes_layout = QHBoxLayout()

        self.pending_label = QLabel(
            "Cambios pendientes: 0"
        )

        self.pending_label.setObjectName(
            "pendingSummary"
        )

        self.view_changes_button = QPushButton(
            "Ver cambios"
        )

        self.undo_button = QPushButton(
            "Deshacer"
        )

        self.discard_button = QPushButton(
            "Descartar todos"
        )

        self.discard_button.setObjectName(
            "dangerButton"
        )

        changes_layout.addWidget(
            self.pending_label,
            1,
        )

        changes_layout.addWidget(
            self.view_changes_button
        )

        changes_layout.addWidget(
            self.undo_button
        )

        changes_layout.addWidget(
            self.discard_button
        )

        layout.addLayout(
            changes_layout
        )

        self.model = (
            PresupuestoTableModel(
                workspace=self._workspace,
                parent=self,
            )
        )

        self.proxy_model = (
            QSortFilterProxyModel(
                self
            )
        )

        self.proxy_model.setSourceModel(
            self.model
        )

        self.proxy_model.setFilterCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )

        self.proxy_model.setFilterKeyColumn(
            -1
        )

        self.proxy_model.setSortRole(
            Qt.ItemDataRole.UserRole
        )

        self.table = QTableView()

        self.table.setModel(
            self.proxy_model
        )

        self.table.setAlternatingRowColors(
            True
        )

        self.table.setSortingEnabled(
            True
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )

        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            |
            QAbstractItemView.EditTrigger.EditKeyPressed
        )

        self.table.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.table.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.table.verticalHeader().setVisible(
            False
        )

        header = (
            self.table.horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )

        header.setDefaultSectionSize(
            150
        )

        header.setMinimumSectionSize(
            80
        )

        layout.addWidget(
            self.table,
            1,
        )

        footer = QHBoxLayout()

        self.status_label = QLabel(
            "Esperando carga del presupuesto..."
        )

        self.status_label.setObjectName(
            "tableStatus"
        )

        self.previous_button = QPushButton(
            "Anterior"
        )

        self.page_label = QLabel(
            "Pagina -"
        )

        self.next_button = QPushButton(
            "Siguiente"
        )

        footer.addWidget(
            self.status_label,
            1,
        )

        footer.addWidget(
            self.previous_button
        )

        footer.addWidget(
            self.page_label
        )

        footer.addWidget(
            self.next_button
        )

        layout.addLayout(
            footer
        )

        self.search_input.textChanged.connect(
            self.proxy_model
            .setFilterFixedString
        )

        self.refresh_button.clicked.connect(
            self.refresh
        )

        self.previous_button.clicked.connect(
            self.previous_page
        )

        self.next_button.clicked.connect(
            self.next_page
        )

        self.page_size_combo.currentTextChanged.connect(
            self._page_size_changed
        )

        self.model.workspace_changed.connect(
            self._on_model_workspace_changed
        )

        self.model.edit_failed.connect(
            self._on_edit_failed
        )

        self.view_changes_button.clicked.connect(
            self.show_pending_changes
        )

        self.undo_button.clicked.connect(
            self.undo_last
        )

        self.discard_button.clicked.connect(
            self.discard_all
        )

        self._update_navigation()
        self._update_change_controls()

    def set_workspace_ready(self):
        self._workspace_ready = True

        self.refresh_button.setEnabled(
            True
        )

        self.status_label.setText(
            "Presupuesto local disponible."
        )

        self._update_navigation()
        self._update_change_controls()

    def set_workspace_error(
        self,
        message: str,
    ):
        self._workspace_ready = False

        self.refresh_button.setEnabled(
            False
        )

        self.previous_button.setEnabled(
            False
        )

        self.next_button.setEnabled(
            False
        )

        self.status_label.setText(
            "Error al preparar presupuesto: "
            + message
        )

    def invalidate(self):
        self._loaded_once = False

    def ensure_loaded(self):
        if (
            self._workspace_ready
            and
            not self._loaded_once
        ):
            self._load_page(0)

    def refresh(self):
        if not self._workspace_ready:
            return

        self._load_page(
            self._page_index
        )

    def previous_page(self):
        if not self._workspace_ready:
            return

        if self._page_index <= 0:
            return

        self._load_page(
            self._page_index - 1
        )

    def next_page(self):
        if not self._workspace_ready:
            return

        total_pages = (
            self._calculate_total_pages()
        )

        if (
            self._page_index
            >= total_pages - 1
        ):
            return

        self._load_page(
            self._page_index + 1
        )

    def _page_size_changed(
        self,
        text: str,
    ):
        self._page_size = int(text)

        if (
            self._workspace_ready
            and
            self._loaded_once
        ):
            self._load_page(0)

    def _load_page(
        self,
        page_index: int,
    ):
        if not self._workspace_ready:
            return

        self._set_loading(True)

        try:
            result = (
                self._analysis_service
                .get_page(
                    page_index=page_index,
                    page_size=self._page_size,
                )
            )

            self.model.set_page(
                result
            )

            self._page_index = (
                result.page_index
            )

            self._total_rows = (
                result.total_rows
            )

            self._loaded_once = True

            self.search_input.clear()

        except Exception as exc:
            self.status_label.setText(
                "Error al cargar datos locales: "
                f"{type(exc).__name__}: {exc}"
            )

        finally:
            self._set_loading(False)

        self._update_navigation()
        self._update_change_controls()

    def _on_model_workspace_changed(
        self,
    ):
        self._update_change_controls()

        self.status_label.setText(
            "Cambio aplicado localmente. "
            "BigQuery no ha sido modificado."
        )

        self.workspace_changed.emit()

    def _on_edit_failed(
        self,
        message: str,
    ):
        self.status_label.setText(
            "No se pudo aplicar el cambio: "
            + message
        )

        QMessageBox.warning(
            self,
            "Cambio no valido",
            message,
        )

    def undo_last(self):
        if not self._workspace.has_changes:
            return

        changed = (
            self._workspace.undo_last()
        )

        if not changed:
            return

        self._load_page(
            self._page_index
        )

        self.status_label.setText(
            "Ultima operacion deshecha."
        )

        self.workspace_changed.emit()

    def discard_all(self):
        if not self._workspace.has_changes:
            return

        result = QMessageBox.question(
            self,
            "Descartar cambios",
            "Se descartaran todos los "
            "cambios realizados durante "
            "esta simulacion.\n\n"
            "¿Desea continuar?",
            QMessageBox.StandardButton.Yes
            |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if (
            result
            != QMessageBox.StandardButton.Yes
        ):
            return

        self._workspace.discard_all()

        self._load_page(
            self._page_index
        )

        self.status_label.setText(
            "Todos los cambios locales "
            "fueron descartados."
        )

        self.workspace_changed.emit()

    def show_pending_changes(self):
        pending = (
            self._workspace
            .get_pending_changes()
        )

        if not pending:
            QMessageBox.information(
                self,
                "Cambios pendientes",
                "No existen cambios pendientes.",
            )
            return

        flattened = []

        for row_change in pending:
            row = self._workspace.get_row(
                row_change.session_row_id
            )

            gasto = (
                row.get("nombre_gasto")
                or ""
            )

            ceco = (
                row.get("ceco")
                or ""
            )

            for change in row_change.changes:
                flattened.append(
                    (
                        row_change.session_row_id,
                        gasto,
                        ceco,
                        change.column,
                        change.before,
                        change.after,
                    )
                )

        total_changes = len(flattened)

        visible_changes = flattened[
            :self.MAX_CHANGE_PREVIEW
        ]

        dialog = QDialog(self)

        dialog.setWindowTitle(
            "Cambios pendientes"
        )

        dialog.resize(
            1050,
            600,
        )

        layout = QVBoxLayout(
            dialog
        )

        summary = QLabel(
            f"{self._workspace.pending_row_count:,} "
            f"filas modificadas | "
            f"{total_changes:,} campos modificados"
        )

        summary.setObjectName(
            "pendingSummary"
        )

        layout.addWidget(
            summary
        )

        if (
            total_changes
            > self.MAX_CHANGE_PREVIEW
        ):
            warning = QLabel(
                "Vista limitada a los primeros "
                f"{self.MAX_CHANGE_PREVIEW:,} cambios."
            )

            warning.setObjectName(
                "tableStatus"
            )

            layout.addWidget(
                warning
            )

        table = QTableWidget(
            len(visible_changes),
            6,
        )

        table.setHorizontalHeaderLabels(
            [
                "ID SESION",
                "GASTO",
                "CECO",
                "CAMPO",
                "ANTES",
                "AHORA",
            ]
        )

        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        table.setAlternatingRowColors(
            True
        )

        table.verticalHeader().setVisible(
            False
        )

        for row_index, values in enumerate(
            visible_changes
        ):
            for column_index, value in enumerate(
                values
            ):
                item = QTableWidgetItem(
                    self._format_value(
                        value
                    )
                )

                table.setItem(
                    row_index,
                    column_index,
                    item,
                )

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        table.horizontalHeader().setStretchLastSection(
            True
        )

        layout.addWidget(
            table,
            1,
        )

        close_button = QPushButton(
            "Cerrar"
        )

        close_button.clicked.connect(
            dialog.accept
        )

        button_layout = QHBoxLayout()

        button_layout.addStretch()

        button_layout.addWidget(
            close_button
        )

        layout.addLayout(
            button_layout
        )

        dialog.exec()

    def _update_change_controls(self):
        if not self._workspace.is_loaded:
            rows = 0
            fields = 0
        else:
            rows = (
                self._workspace
                .pending_row_count
            )

            fields = (
                self._workspace
                .pending_change_count
            )

        self.pending_label.setText(
            f"Cambios pendientes: "
            f"{rows:,} filas / "
            f"{fields:,} campos"
        )

        has_changes = (
            rows > 0
        )

        self.view_changes_button.setEnabled(
            has_changes
        )

        self.undo_button.setEnabled(
            has_changes
        )

        self.discard_button.setEnabled(
            has_changes
        )

    def _set_loading(
        self,
        loading: bool,
    ):
        self.refresh_button.setEnabled(
            self._workspace_ready
            and
            not loading
        )

        self.page_size_combo.setEnabled(
            not loading
        )

        if loading:
            self.previous_button.setEnabled(
                False
            )

            self.next_button.setEnabled(
                False
            )

        else:
            self._update_navigation()

    def _calculate_total_pages(self):
        if self._total_rows == 0:
            return 1

        return (
            self._total_rows
            + self._page_size
            - 1
        ) // self._page_size

    def _update_navigation(self):
        if not self._workspace_ready:
            self.previous_button.setEnabled(
                False
            )

            self.next_button.setEnabled(
                False
            )

            self.page_label.setText(
                "Pagina -"
            )

            return

        total_pages = (
            self._calculate_total_pages()
        )

        self.previous_button.setEnabled(
            self._page_index > 0
        )

        self.next_button.setEnabled(
            self._page_index
            < total_pages - 1
        )

        self.page_label.setText(
            f"Pagina "
            f"{self._page_index + 1} "
            f"de {total_pages}"
        )

        if self._total_rows == 0:
            self.status_label.setText(
                "Sin registros"
            )

            return

        first_row = (
            self._page_index
            * self._page_size
            + 1
        )

        last_row = min(
            first_row
            + self._page_size
            - 1,
            self._total_rows,
        )

        self.status_label.setText(
            f"Mostrando "
            f"{first_row:,} - "
            f"{last_row:,} "
            f"de "
            f"{self._total_rows:,} "
            f"registros locales"
        )

    @staticmethod
    def _format_value(
        value,
    ) -> str:
        if value is None:
            return ""

        if isinstance(value, Decimal):
            return f"{value:,.2f}"

        if isinstance(value, bool):
            return (
                "Si"
                if value
                else "No"
            )

        return str(value)