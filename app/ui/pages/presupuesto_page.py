from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import (
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
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

from app.services.current_actor_service import (
    CurrentActorError,
    resolve_current_actor,
)
from app.services.new_budget_row_service import (
    NewBudgetRowService,
)
from app.services.presupuesto_change_summary_service import (
    PresupuestoChangeSummaryService,
)
from app.ui.dialogs.budget_excel_import_dialog import (
    BudgetExcelImportDialog,
)
from app.ui.dialogs.change_summary_dialog import (
    ChangeSummaryDialog,
)
from app.ui.dialogs.monthly_distribution_dialog import (
    MonthlyDistributionDialog,
)
from app.ui.dialogs.new_budget_row_dialog import (
    NewBudgetRowDialog,
)
from app.ui.models.presupuesto_table_model import (
    PresupuestoTableModel,
)
from app.ui.workers.budget_catalog_loader import (
    BudgetCatalogLoadThread,
)
from app.ui.workers.budget_excel_import import (
    BudgetExcelImportThread,
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

        self._change_summary_service = (
            PresupuestoChangeSummaryService(
                workspace
            )
        )

        self._page_index = 0
        self._page_size = 250
        self._total_rows = 0

        self._workspace_ready = False
        self._loaded_once = False

        self._new_row_catalog_thread = None
        self._new_row_actor = None

        self._excel_import_thread = None
        self._excel_import_actor = None
        self._excel_import_path = None

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
            "Modifica importes en USD y "
            "prepara nuevas filas. Todos los "
            "cambios permanecen locales hasta "
            "usar Aplicar cambios."
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

        self.new_row_button = QPushButton(
            "Nueva fila"
        )

        self.new_row_button.setObjectName(
            "primaryButton"
        )

        self.new_row_button.setEnabled(
            False
        )

        self.import_excel_button = QPushButton(
            "Importar Excel"
        )

        self.import_excel_button.setEnabled(
            False
        )

        self.distribute_months_button = (
            QPushButton(
                "Distribuir meses"
            )
        )

        self.distribute_months_button.setEnabled(
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
            self.new_row_button
        )

        toolbar.addWidget(
            self.import_excel_button
        )

        toolbar.addWidget(
            self.distribute_months_button
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

        self.new_row_button.clicked.connect(
            self.show_new_row_dialog
        )

        self.import_excel_button.clicked.connect(
            self.show_excel_import
        )

        self.distribute_months_button.clicked.connect(
            self.show_monthly_distribution
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

        self.table.selectionModel().currentChanged.connect(
            self._on_table_selection_changed
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

    @property
    def is_busy(
        self,
    ) -> bool:
        catalog_busy = (
            self._new_row_catalog_thread
            is not None
            and
            self._new_row_catalog_thread
            .isRunning()
        )

        import_busy = (
            self._excel_import_thread
            is not None
            and
            self._excel_import_thread
            .isRunning()
        )

        return bool(
            catalog_busy
            or import_busy
        )

    def set_workspace_ready(self):
        self._workspace_ready = True

        self.refresh_button.setEnabled(
            True
        )

        self._update_new_row_button()
        self._update_import_excel_button()

        self.status_label.setText(
            "Presupuesto local disponible."
        )

        self._update_navigation()
        self._update_change_controls()
        self._update_distribution_button()

    def set_workspace_error(
        self,
        message: str,
    ):
        self._workspace_ready = False

        self.refresh_button.setEnabled(
            False
        )

        self.new_row_button.setEnabled(
            False
        )

        self.import_excel_button.setEnabled(
            False
        )

        self.previous_button.setEnabled(
            False
        )

        self.next_button.setEnabled(
            False
        )

        self.distribute_months_button.setEnabled(
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
        self._update_distribution_button()

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

    def _on_table_selection_changed(
        self,
        *_,
    ):
        self._update_distribution_button()

    def _update_distribution_button(
        self,
    ):
        enabled = (
            self._workspace_ready
            and
            self._workspace.is_loaded
            and
            self._workspace
            .module_config
            .capabilities
            .monthly_distribution
            and
            self.table.currentIndex().isValid()
        )

        self.distribute_months_button.setEnabled(
            bool(enabled)
        )

    def _update_import_excel_button(
        self,
    ):
        if not hasattr(
            self,
            "import_excel_button",
        ):
            return

        enabled = (
            self._workspace_ready
            and
            self._workspace.is_loaded
            and
            not self.is_busy
        )

        self.import_excel_button.setEnabled(
            enabled
        )

        if (
            self._excel_import_thread
            is not None
            and
            self._excel_import_thread
            .isRunning()
        ):
            self.import_excel_button.setText(
                "Validando Excel..."
            )

        else:
            self.import_excel_button.setText(
                "Importar Excel"
            )

    def show_excel_import(
        self,
    ):
        if not (
            self._workspace_ready
            and self._workspace.is_loaded
        ):
            return

        if self.is_busy:
            return

        file_path, _ = (
            QFileDialog
            .getOpenFileName(
                self,
                "Seleccionar Excel "
                f"{self._workspace.module_config.label}",
                "",
                (
                    "Excel (*.xlsx *.xlsm);;"
                    "Todos los archivos (*.*)"
                ),
            )
        )

        if not file_path:
            return

        try:
            actor = (
                resolve_current_actor()
            )

        except CurrentActorError as exc:
            QMessageBox.warning(
                self,
                "Usuario no identificado",
                str(exc),
            )
            return

        self._excel_import_actor = (
            actor
        )

        self._excel_import_path = (
            file_path
        )

        self._excel_import_thread = (
            BudgetExcelImportThread(
                module_config=(
                    self._workspace
                    .module_config
                ),
                file_path=file_path,
                actor=actor,
                parent=self,
            )
        )

        self._excel_import_thread.loaded.connect(
            self._on_excel_import_loaded
        )

        self._excel_import_thread.failed.connect(
            self._on_excel_import_failed
        )

        self._excel_import_thread.finished.connect(
            self._on_excel_import_finished
        )

        self.status_label.setText(
            "Leyendo, limpiando y validando "
            f"{Path(file_path).name}..."
        )

        self._update_new_row_button()
        self._update_import_excel_button()

        self._excel_import_thread.start()

    def _on_excel_import_loaded(
        self,
        result,
    ):
        dialog = (
            BudgetExcelImportDialog(
                result=result,
                module_config=(
                    self._workspace
                    .module_config
                ),
                parent=self,
            )
        )

        accepted = (
            dialog.exec()
        )

        if not accepted:
            self.status_label.setText(
                "Importacion cancelada. "
                "No se agregaron filas."
            )

            self._excel_import_actor = None
            self._excel_import_path = None

            return

        if not result.is_valid:
            self._excel_import_actor = None
            self._excel_import_path = None
            return

        source_name = (
            Path(
                result.source_path
            )
            .name
        )

        try:
            session_ids = (
                self._workspace
                .add_new_rows(
                    result.rows,
                    description=(
                        "Importar Excel "
                        f"{source_name}"
                    ),
                )
            )

        except Exception as exc:
            QMessageBox.warning(
                self,
                "No se pudo importar",
                "La validacion del Excel "
                "finalizo, pero las filas "
                "no pudieron agregarse "
                "al Workspace.\n\n"
                f"{type(exc).__name__}: "
                f"{exc}",
            )

            self._excel_import_actor = None
            self._excel_import_path = None

            return

        last_page = max(
            0,
            (
                self._workspace.row_count
                - 1
            )
            // self._page_size,
        )

        self._load_page(
            last_page
        )

        if session_ids:
            self._select_session_row(
                session_ids[-1]
            )

        self.status_label.setText(
            f"{len(session_ids):,} filas "
            "agregadas al Workspace desde "
            f"{source_name}. "
            "BigQuery todavia no ha sido "
            "modificado."
        )

        self.workspace_changed.emit()

        self._excel_import_actor = None
        self._excel_import_path = None

    def _on_excel_import_failed(
        self,
        message,
    ):
        QMessageBox.warning(
            self,
            "No se pudo validar el Excel",
            "El archivo no pudo prepararse "
            "para importacion.\n\n"
            f"Detalle: {message}",
        )

        self.status_label.setText(
            "Importacion Excel fallida. "
            "No se realizaron cambios."
        )

        self._excel_import_actor = None
        self._excel_import_path = None

    def _on_excel_import_finished(
        self,
    ):
        if (
            self._excel_import_thread
            is not None
        ):
            self._excel_import_thread.deleteLater()

            self._excel_import_thread = None

        self._update_new_row_button()
        self._update_import_excel_button()

    def _update_new_row_button(
        self,
    ):
        if not hasattr(
            self,
            "new_row_button",
        ):
            return

        busy = self.is_busy

        enabled = (
            self._workspace_ready
            and
            self._workspace.is_loaded
            and
            not busy
        )

        self.new_row_button.setEnabled(
            enabled
        )

        if busy:
            self.new_row_button.setText(
                "Cargando catalogos..."
            )

        else:
            self.new_row_button.setText(
                "Nueva fila"
            )

    def show_new_row_dialog(
        self,
    ):
        if not (
            self._workspace_ready
            and self._workspace.is_loaded
        ):
            return

        if self.is_busy:
            return

        try:
            actor = (
                resolve_current_actor()
            )

        except CurrentActorError as exc:
            QMessageBox.warning(
                self,
                "Usuario no identificado",
                str(exc),
            )
            return

        self._new_row_actor = (
            actor
        )

        self._new_row_catalog_thread = (
            BudgetCatalogLoadThread(
                self._workspace
                .module_config,
                parent=self,
            )
        )

        self._new_row_catalog_thread.loaded.connect(
            self._on_new_row_catalogs_loaded
        )

        self._new_row_catalog_thread.failed.connect(
            self._on_new_row_catalogs_failed
        )

        self._new_row_catalog_thread.finished.connect(
            self._on_new_row_catalogs_finished
        )

        self.status_label.setText(
            "Cargando catalogos para "
            "la nueva fila..."
        )

        self._update_new_row_button()
        self._update_import_excel_button()

        self._new_row_catalog_thread.start()

    def _on_new_row_catalogs_loaded(
        self,
        catalogs,
    ):
        self._open_new_row_dialog(
            catalogs
        )

    def _on_new_row_catalogs_failed(
        self,
        message,
    ):
        QMessageBox.warning(
            self,
            "Catalogos no disponibles",
            "No se pudieron cargar los "
            "catalogos desde BigQuery.\n\n"
            "El formulario puede continuar "
            "con campos libres.\n\n"
            f"Detalle: {message}",
        )

        self._open_new_row_dialog(
            {}
        )

    def _on_new_row_catalogs_finished(
        self,
    ):
        if (
            self._new_row_catalog_thread
            is not None
        ):
            self._new_row_catalog_thread.deleteLater()

            self._new_row_catalog_thread = None

        self._new_row_actor = None

        self._update_new_row_button()
        self._update_import_excel_button()

    def _open_new_row_dialog(
        self,
        catalogs,
    ):
        actor = (
            self._new_row_actor
        )

        if not actor:
            return

        dialog = (
            NewBudgetRowDialog(
                module_config=(
                    self._workspace
                    .module_config
                ),
                catalogs=catalogs,
                parent=self,
            )
        )

        if not dialog.exec():
            self.status_label.setText(
                "Alta cancelada. "
                "No se realizaron cambios."
            )
            return

        try:
            draft = (
                NewBudgetRowService(
                    self._workspace
                    .module_config
                )
                .create_draft(
                    dialog.dimensions(),
                    actor=actor,
                )
            )

            session_row_id = (
                self._workspace
                .add_new_row(
                    draft.row
                )
            )

        except Exception as exc:
            QMessageBox.warning(
                self,
                "No se pudo crear la fila",
                "La nueva fila no pudo "
                "agregarse al Workspace.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        last_page = max(
            0,
            (
                self._workspace.row_count
                - 1
            )
            // self._page_size,
        )

        self._load_page(
            last_page
        )

        self._select_session_row(
            session_row_id
        )

        self.status_label.setText(
            "Nueva fila creada localmente. "
            "Los importes iniciales son 0. "
            "Puedes editar USD o usar "
            "Distribuir meses. BigQuery "
            "todavia no ha sido modificado."
        )

        self.workspace_changed.emit()

    def _select_session_row(
        self,
        session_row_id,
    ):
        for source_row in range(
            self.model.rowCount()
        ):
            if (
                self.model
                .session_row_id(
                    source_row
                )
                != session_row_id
            ):
                continue

            source_index = (
                self.model.index(
                    source_row,
                    0,
                )
            )

            proxy_index = (
                self.proxy_model
                .mapFromSource(
                    source_index
                )
            )

            if not proxy_index.isValid():
                return

            self.table.setCurrentIndex(
                proxy_index
            )

            self.table.scrollTo(
                proxy_index,
                QAbstractItemView
                .ScrollHint
                .PositionAtCenter,
            )

            return

    def show_monthly_distribution(
        self,
    ):
        if not (
            self._workspace
            .module_config
            .capabilities
            .monthly_distribution
        ):
            QMessageBox.information(
                self,
                "Distribucion mensual",
                "El modulo activo no permite "
                "distribucion mensual.",
            )
            return

        proxy_index = (
            self.table.currentIndex()
        )

        if not proxy_index.isValid():
            QMessageBox.information(
                self,
                "Distribucion mensual",
                "Selecciona primero una fila "
                "del presupuesto.",
            )
            return

        source_index = (
            self.proxy_model
            .mapToSource(
                proxy_index
            )
        )

        session_row_id = (
            self.model.session_row_id(
                source_index.row()
            )
        )

        if session_row_id is None:
            QMessageBox.warning(
                self,
                "Distribucion mensual",
                "No se pudo identificar "
                "la fila seleccionada.",
            )
            return

        try:
            row = (
                self._workspace
                .get_row(
                    session_row_id
                )
            )

            dialog = (
                MonthlyDistributionDialog(
                    row=row,
                    module_config=(
                        self._workspace
                        .module_config
                    ),
                    parent=self,
                )
            )

            if not dialog.exec():
                return

            changed = (
                self._workspace
                .edit_monthly_distribution(
                    session_row_id,
                    dialog.percentages(),
                    annual_total=(
                        dialog.annual_total()
                    ),
                )
            )

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Distribucion mensual",
                "No se pudo aplicar "
                "la distribucion.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        if not changed:
            self.status_label.setText(
                "La distribucion mensual "
                "no produjo cambios."
            )
            return

        self._load_page(
            self._page_index
        )

        self.status_label.setText(
            "Distribucion mensual aplicada "
            "localmente. BigQuery no ha sido "
            "modificado."
        )

        self.workspace_changed.emit()

    def show_pending_changes(self):
        if not self._workspace.has_changes:
            QMessageBox.information(
                self,
                "Cambios pendientes",
                "No existen cambios pendientes.",
            )
            return

        try:
            summary = (
                self._change_summary_service
                .build()
            )

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Cambios pendientes",
                "No se pudo generar "
                "el resumen de cambios.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        dialog = ChangeSummaryDialog(
            summary,
            self,
            module_label=(
                self._workspace
                .module_config
                .label
            ),
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

        self._update_new_row_button()
        self._update_import_excel_button()

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
