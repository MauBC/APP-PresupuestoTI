from PySide6.QtCore import (
    Qt,
    QTimer,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config.budget_module_config import (
    BudgetModule,
)
from app.config.budget_modules import (
    get_budget_module_config,
)
from app.config.settings import settings
from app.services.current_actor_service import (
    CurrentActorError,
    resolve_current_actor,
)
from app.services.presupuesto_change_summary_service import (
    PresupuestoChangeSummaryService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_analysis_service import (
    PresupuestoWorkspaceAnalysisService,
)
from app.ui.dialogs.app_message_box import (
    show_error,
    show_info,
    show_warning,
)
from app.ui.dialogs.apply_changes_dialog import (
    ApplyChangesDialog,
)
from app.ui.dialogs.reversal_confirm_dialog import (
    ReversalConfirmDialog,
)
from app.ui.pages.aggregation_page import (
    AggregationPage,
)
from app.ui.pages.dashboard_page import (
    DashboardPage,
)
from app.ui.pages.history_page import (
    HistoryPage,
)
from app.ui.pages.presupuesto_page import (
    PresupuestoPage,
)
from app.ui.workers.presupuesto_reversal import (
    PresupuestoReversalThread,
)
from app.ui.workers.presupuesto_save import (
    PresupuestoSaveThread,
)
from app.ui.workers.workspace_loader import (
    WorkspaceLoadThread,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            settings.APP_NAME
        )

        self.resize(
            settings.WINDOW_WIDTH,
            settings.WINDOW_HEIGHT,
        )

        self.active_module = (
            get_budget_module_config(
                BudgetModule.OPEX
            )
        )

        self.workspace = (
            PresupuestoWorkspace(
                self.active_module
            )
        )

        self.analysis_service = (
            PresupuestoWorkspaceAnalysisService(
                self.workspace
            )
        )

        self.change_summary_service = (
            PresupuestoChangeSummaryService(
                self.workspace
            )
        )

        self._workspace_loader = None
        self._save_thread = None
        self._reversal_thread = None

        self._save_in_progress = False
        self._reversal_in_progress = False

        self._reload_after_applied_failure = False
        self._reversal_reload_after_applied_failure = False

        self._initial_load_seconds = None

        self._setup_ui()

        QTimer.singleShot(
            0,
            self._start_workspace_load,
        )

    def _setup_ui(self):
        central_widget = QWidget()

        self.setCentralWidget(
            central_widget
        )

        main_layout = QHBoxLayout(
            central_widget
        )

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        main_layout.setSpacing(0)

        sidebar = self._create_sidebar()

        content_widget = QWidget()

        content_layout = QVBoxLayout(
            content_widget
        )

        content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        content_layout.setSpacing(0)

        self.workspace_banner = QLabel(
            "Preparando presupuesto..."
        )

        self.workspace_banner.setObjectName(
            "analysisSummary"
        )

        self.workspace_banner.setWordWrap(
            True
        )

        self.pages = QStackedWidget()

        self.dashboard_page = (
            DashboardPage(
                self.analysis_service
            )
        )

        self.presupuesto_page = (
            PresupuestoPage(
                workspace=self.workspace,
                analysis_service=(
                    self.analysis_service
                ),
            )
        )

        self.aggregation_page = (
            AggregationPage(
                workspace=self.workspace,
                analysis_service=(
                    self.analysis_service
                ),
            )
        )

        self.history_page = (
            HistoryPage(
                module_config=(
                    self.active_module
                )
            )
        )

        self.history_page.reversal_requested.connect(
            self._request_history_reversal
        )

        self.presupuesto_page.workspace_changed.connect(
            self._on_workspace_changed
        )

        self.aggregation_page.workspace_changed.connect(
            self._on_workspace_changed
        )

        self.pages.addWidget(
            self.dashboard_page
        )

        self.pages.addWidget(
            self.presupuesto_page
        )

        self.pages.addWidget(
            self.aggregation_page
        )

        self.pages.addWidget(
            self.history_page
        )

        content_layout.addWidget(
            self.workspace_banner
        )

        content_layout.addWidget(
            self.pages,
            1,
        )

        main_layout.addWidget(
            sidebar
        )

        main_layout.addWidget(
            content_widget,
            1,
        )

    def _create_sidebar(self):
        sidebar = QFrame()

        sidebar.setObjectName(
            "sidebar"
        )

        sidebar.setFixedWidth(
            settings.SIDEBAR_WIDTH
        )

        layout = QVBoxLayout(
            sidebar
        )

        layout.setContentsMargins(
            18,
            26,
            18,
            24,
        )

        layout.setSpacing(8)

        title = QLabel(
            "Presupuesto TI"
        )

        title.setObjectName(
            "appTitle"
        )

        subtitle = QLabel(
            "Gestion presupuestal"
        )

        subtitle.setObjectName(
            "appSubtitle"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(18)

        module_selector = (
            self._create_module_selector()
        )

        layout.addWidget(
            module_selector
        )

        layout.addSpacing(18)

        self.button_group = (
            QButtonGroup(self)
        )

        self.button_group.setExclusive(
            True
        )

        dashboard_button = (
            self._create_nav_button(
                "Dashboard",
                0,
            )
        )

        presupuesto_button = (
            self._create_nav_button(
                "Presupuesto",
                1,
            )
        )

        aggregation_button = (
            self._create_nav_button(
                "Agrupaciones",
                2,
            )
        )

        history_button = (
            self._create_nav_button(
                "Historial",
                3,
            )
        )

        layout.addWidget(
            dashboard_button
        )

        layout.addWidget(
            presupuesto_button
        )

        layout.addWidget(
            aggregation_button
        )

        layout.addWidget(
            history_button
        )

        layout.addStretch()

        self.apply_changes_button = QPushButton(
            "Aplicar cambios"
        )

        self.apply_changes_button.setEnabled(
            False
        )

        self.apply_changes_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.apply_changes_button.setToolTip(
            "Confirma los cambios pendientes "
            "antes de enviarlos a BigQuery."
        )

        self.apply_changes_button.setStyleSheet(
            """
            QPushButton {
                background-color: #2F7650;
                color: #FFFFFF;
                border: 1px solid #2F7650;
                border-radius: 7px;
                padding: 10px 8px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: #285F42;
            }

            QPushButton:disabled {
                background-color: #D0D5DD;
                color: #667085;
                border-color: #D0D5DD;
            }
            """
        )

        self.apply_changes_button.clicked.connect(
            self._show_apply_changes_dialog
        )

        layout.addWidget(
            self.apply_changes_button
        )

        layout.addSpacing(8)

        version_label = QLabel(
            f"Version {settings.APP_VERSION}"
        )

        version_label.setObjectName(
            "appSubtitle"
        )

        layout.addWidget(
            version_label
        )

        dashboard_button.setChecked(
            True
        )

        return sidebar

    def _create_module_selector(
        self,
    ):
        container = QFrame()

        container.setObjectName(
            "moduleSelector"
        )

        layout = QHBoxLayout(
            container
        )

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(
            6
        )

        self.module_button_group = (
            QButtonGroup(self)
        )

        self.module_button_group.setExclusive(
            True
        )

        self.opex_module_button = (
            self._create_module_button(
                "OPEX",
                BudgetModule.OPEX,
            )
        )

        self.capex_module_button = (
            self._create_module_button(
                "CAPEX",
                BudgetModule.CAPEX,
            )
        )

        layout.addWidget(
            self.opex_module_button
        )

        layout.addWidget(
            self.capex_module_button
        )

        self._sync_module_selector()

        return container

    def _create_module_button(
        self,
        text: str,
        module: BudgetModule,
    ):
        button = QPushButton(
            text
        )

        button.setCheckable(
            True
        )

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button.setStyleSheet(
            """
            QPushButton {
                background-color: #FFFFFF;
                color: #344054;
                border: 1px solid #D0D5DD;
                border-radius: 7px;
                padding: 8px 6px;
                font-weight: 700;
            }

            QPushButton:hover {
                border-color: #2F7650;
                color: #2F7650;
            }

            QPushButton:checked {
                background-color: #2F7650;
                color: #FFFFFF;
                border-color: #2F7650;
            }
            """
        )

        button.clicked.connect(
            lambda checked=False, value=module:
            self._select_budget_module(
                value
            )
        )

        self.module_button_group.addButton(
            button
        )

        return button

    def _select_budget_module(
        self,
        module: BudgetModule,
    ):
        if (
            self._save_in_progress
            or self._reversal_in_progress
        ):
            self._sync_module_selector()
            return

        config = (
            get_budget_module_config(
                module
            )
        )

        if (
            config.module
            == self.active_module.module
        ):
            self._sync_module_selector()
            return

        if not config.configured:
            show_info(
                self,
                "CAPEX",
                "El modulo CAPEX ya esta "
                "contemplado en la arquitectura, "
                "pero todavia no se ha conectado "
                "su esquema de proyectos.\n\n"
                "OPEX continuara activo.",
            )

            self._sync_module_selector()
            return

        if (
            self.workspace.is_loaded
            and self.workspace.has_changes
        ):
            show_warning(
                self,
                "Cambios pendientes",
                "No se puede cambiar de modulo "
                "mientras existan cambios locales "
                "sin aplicar.\n\n"
                "Aplica o descarta los cambios "
                "antes de continuar.",
            )

            self._sync_module_selector()
            return

        self.active_module = config
        self._sync_module_selector()

    def _sync_module_selector(
        self,
    ):
        is_opex = (
            self.active_module.module
            == BudgetModule.OPEX
        )

        self.opex_module_button.setChecked(
            is_opex
        )

        self.capex_module_button.setChecked(
            not is_opex
        )

    def _create_nav_button(
        self,
        text: str,
        page_index: int,
    ):
        button = QPushButton(text)

        button.setObjectName(
            "sidebarButton"
        )

        button.setCheckable(True)

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button.clicked.connect(
            lambda checked=False, index=page_index:
            self._navigate_to(index)
        )

        self.button_group.addButton(
            button
        )

        return button

    def _navigate_to(
        self,
        page_index: int,
    ):
        self.pages.setCurrentIndex(
            page_index
        )

        page = self.pages.currentWidget()

        if hasattr(
            page,
            "ensure_loaded",
        ):
            page.ensure_loaded()

    def _start_workspace_load(self):
        if (
            self._workspace_loader is not None
            and self._workspace_loader.isRunning()
        ):
            return

        self.pages.setEnabled(
            False
        )

        self._update_apply_button(
            0
        )

        self.workspace_banner.setText(
            f"{self.active_module.label}  |  "
            "Cargando presupuesto "
            "desde BigQuery..."
        )

        self._workspace_loader = (
            WorkspaceLoadThread(
                workspace=self.workspace,
                parent=self,
            )
        )

        self._workspace_loader.loaded.connect(
            self._on_workspace_loaded
        )

        self._workspace_loader.failed.connect(
            self._on_workspace_failed
        )

        self._workspace_loader.finished.connect(
            self._on_workspace_finished
        )

        self._workspace_loader.start()

    def _on_workspace_loaded(
        self,
        result,
    ):
        self._initial_load_seconds = (
            result.total_seconds
        )

        self.pages.setEnabled(
            True
        )

        self.dashboard_page.set_workspace_ready()
        self.presupuesto_page.set_workspace_ready()
        self.aggregation_page.set_workspace_ready()

        self._update_workspace_banner()

        page = self.pages.currentWidget()

        if hasattr(
            page,
            "ensure_loaded",
        ):
            page.ensure_loaded()

    def _on_workspace_changed(self):
        self._invalidate_page(
            self.dashboard_page
        )

        self._invalidate_page(
            self.presupuesto_page
        )

        self._invalidate_page(
            self.aggregation_page
        )

        self._update_workspace_banner()

    @staticmethod
    def _invalidate_page(
        page,
    ):
        if hasattr(
            page,
            "invalidate",
        ):
            page.invalidate()

    def _update_workspace_banner(self):
        if not self.workspace.is_loaded:
            self._update_apply_button(
                0
            )
            return

        pending_rows = (
            self.workspace.pending_row_count
        )

        pending_fields = (
            self.workspace.pending_change_count
        )

        text = (
            f"{self.active_module.label}  |  "
            "MODO EDICION LOCAL  |  "
            f"{self.workspace.row_count:,} registros"
        )

        if (
            self._initial_load_seconds
            is not None
        ):
            text += (
                "  |  "
                f"Carga inicial: "
                f"{self._initial_load_seconds:.2f} s"
            )

        if pending_rows > 0:
            text += (
                "  |  "
                f"Cambios: "
                f"{pending_rows:,} filas / "
                f"{pending_fields:,} campos"
            )
        else:
            text += (
                "  |  Sin cambios pendientes"
            )

        if pending_rows > 0:
            text += (
                "  |  BigQuery pendiente "
                "de sincronizacion"
            )
        else:
            text += (
                "  |  BigQuery sincronizado"
            )

        self.workspace_banner.setText(
            text
        )

        self._update_apply_button(
            pending_rows
        )

    def _update_apply_button(
        self,
        pending_rows: int,
    ):
        if (
            self._save_in_progress
            or self._reversal_in_progress
        ):
            self.apply_changes_button.setEnabled(
                False
            )

            if self._save_in_progress:
                text = "Guardando cambios..."
            else:
                text = "Revirtiendo cambios..."

            self.apply_changes_button.setText(
                text
            )

            return

        has_changes = (
            pending_rows > 0
        )

        self.apply_changes_button.setEnabled(
            has_changes
        )

        if has_changes:
            self.apply_changes_button.setText(
                "Aplicar cambios "
                f"({pending_rows:,})"
            )
        else:
            self.apply_changes_button.setText(
                "Aplicar cambios"
            )

    def _show_apply_changes_dialog(self):
        if self._save_in_progress:
            return

        if not self.workspace.is_loaded:
            show_info(
                self,
                f"Aplicar cambios {self.active_module.label}",
                "El presupuesto todavia "
                "no se encuentra cargado.",
            )
            return

        if not self.workspace.has_changes:
            show_info(
                self,
                f"Aplicar cambios {self.active_module.label}",
                "No existen cambios pendientes.",
            )
            return

        try:
            actor = resolve_current_actor()

        except CurrentActorError as exc:
            show_warning(
                self,
                "Usuario no identificado",
                str(exc),
            )
            return

        try:
            summary = (
                self.change_summary_service
                .build()
            )

        except Exception as exc:
            show_warning(
                self,
                "Aplicar cambios OPEX",
                "No se pudo preparar el "
                "resumen de cambios.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        dialog = ApplyChangesDialog(
            summary,
            actor,
            self,
            module_label=(
                self.active_module.label
            ),
        )

        if not dialog.exec():
            return

        self._start_presupuesto_save(
            actor
        )

    def _request_history_reversal(
        self,
        batch,
    ):
        if (
            self._save_in_progress
            or self._reversal_in_progress
        ):
            return

        if not self.workspace.is_loaded:
            show_info(
                self,
                "Revertir cambios",
                "El presupuesto todav\u00eda "
                "no se encuentra cargado.",
            )
            return

        if self.workspace.has_changes:
            show_warning(
                self,
                "Cambios locales pendientes",
                "No se puede revertir un batch "
                "mientras existan cambios locales "
                "sin aplicar.\n\n"
                "Aplica o descarta esos cambios "
                "antes de continuar.",
            )
            return

        if (
            str(batch.status)
            .strip()
            .upper()
            != "APPLIED"
        ):
            show_warning(
                self,
                "Batch no reversible",
                "Solo pueden revertirse "
                "operaciones con estado APPLIED.",
            )
            return

        if batch.reverted_batch_id:
            show_warning(
                self,
                "Batch de reversi\u00f3n",
                "La operaci\u00f3n seleccionada ya "
                "corresponde a una reversi\u00f3n.",
            )
            return

        try:
            actor = resolve_current_actor()

        except CurrentActorError as exc:
            show_warning(
                self,
                "Usuario no identificado",
                str(exc),
            )
            return

        dialog = ReversalConfirmDialog(
            batch,
            self,
        )

        if not dialog.exec():
            return

        self._start_history_reversal(
            batch,
            actor,
        )

    def _set_navigation_enabled(
        self,
        enabled: bool,
    ):
        for group_name in (
            "button_group",
            "module_button_group",
        ):
            group = getattr(
                self,
                group_name,
                None,
            )

            if group is None:
                continue

            for button in group.buttons():
                button.setEnabled(
                    enabled
                )

    def _start_history_reversal(
        self,
        batch,
        actor: str,
    ):
        if (
            self._reversal_thread
            is not None
            and self._reversal_thread
            .isRunning()
        ):
            return

        if (
            self._save_in_progress
            or self.workspace.has_changes
        ):
            return

        self._reversal_in_progress = True

        self._reversal_reload_after_applied_failure = (
            False
        )

        self.pages.setEnabled(
            False
        )

        self._set_navigation_enabled(
            False
        )

        self.workspace_banner.setText(
            f"{self.active_module.label}  |  "
            "Revirtiendo batch en BigQuery..."
        )

        self._update_apply_button(
            self.workspace.pending_row_count
        )

        self._reversal_thread = (
            PresupuestoReversalThread(
                workspace=self.workspace,
                batch=batch,
                actor=actor,
                parent=self,
            )
        )

        self._reversal_thread.completed.connect(
            self._on_history_reversal_completed
        )

        self._reversal_thread.failed.connect(
            self._on_history_reversal_failed
        )

        self._reversal_thread.finished.connect(
            self._on_history_reversal_finished
        )

        self._reversal_thread.start()

    def _on_history_reversal_completed(
        self,
        outcome,
    ):
        result = (
            outcome.persistence_result
        )

        self._invalidate_page(
            self.history_page
        )

        if result.status == "APPLIED":
            self._invalidate_page(
                self.dashboard_page
            )

            self._invalidate_page(
                self.presupuesto_page
            )

            self._invalidate_page(
                self.aggregation_page
            )

            self.dashboard_page.set_workspace_ready()
            self.presupuesto_page.set_workspace_ready()
            self.aggregation_page.set_workspace_ready()

            self._update_workspace_banner()

            show_info(
                self,
                "Reversi\u00f3n aplicada",
                "La reversi\u00f3n se aplic\u00f3 "
                "correctamente en BigQuery.\n\n"
                f"Batch original: "
                f"{outcome.source_batch.batch_id}\n"
                f"Nuevo batch: "
                f"{result.batch_id}\n"
                f"Filas revertidas: "
                f"{result.row_count:,}\n"
                f"Campos revertidos: "
                f"{result.field_count:,}",
            )

            return

        if result.status == "CONFLICT":
            conflicts = (
                result.conflicts
            )

            preview_lines = []

            for conflict in conflicts[:5]:
                current = (
                    conflict.current_version
                    if conflict.current_version
                    is not None
                    else "no encontrada"
                )

                preview_lines.append(
                    f"- {conflict.row_id}: "
                    f"esperada "
                    f"{conflict.expected_version}, "
                    f"actual {current}"
                )

            preview = "\n".join(
                preview_lines
            )

            if len(conflicts) > 5:
                preview += "\n- ..."

            show_warning(
                self,
                "Reversi\u00f3n bloqueada",
                "No se revirti\u00f3 ning?n dato.\n\n"
                "Una o m\u00e1s filas fueron "
                "modificadas despu\u00e9s del batch "
                "seleccionado.\n\n"
                f"Conflictos: "
                f"{len(conflicts):,}\n\n"
                f"{preview}",
            )

            self._update_workspace_banner()
            return

        if result.status == "FAILED":
            show_error(
                self,
                "No se pudo revertir",
                "BigQuery rechaz? o revirti\u00f3 "
                "la operaci\u00f3n.\n\n"
                "Los datos vigentes no fueron "
                "reemplazados por la reversi\u00f3n.\n\n"
                f"Detalle: "
                f"{result.error_message}",
            )

            self._update_workspace_banner()
            return

        show_warning(
            self,
            "Resultado no reconocido",
            "La reversi\u00f3n termin\u00f3 con un "
            "estado inesperado:\n\n"
            f"{result.status}",
        )

    def _on_history_reversal_failed(
        self,
        failure,
    ):
        self._invalidate_page(
            self.history_page
        )

        if failure.was_applied:
            self._reversal_reload_after_applied_failure = (
                True
            )

            self.workspace_banner.setText(
                f"{self.active_module.label}  |  "
                "Reversi\u00f3n aplicada en BigQuery  |  "
                "Recarga pendiente"
            )

            show_warning(
                self,
                "Reversi\u00f3n aplicada, recarga pendiente",
                "La reversi\u00f3n SI fue aplicada "
                "en BigQuery, pero fall\u00f3 la "
                "recarga del Workspace.\n\n"
                "No vuelvas a revertir el mismo "
                "batch.\n\n"
                "La aplicaci\u00f3n intentar? recargar "
                "el presupuesto nuevamente.\n\n"
                f"Batch nuevo: "
                f"{failure.batch_id}",
            )

            return

        show_error(
            self,
            "Error al revertir",
            "No se pudo completar la "
            "reversi\u00f3n.\n\n"
            f"Detalle: {failure.message}",
        )

        self._update_workspace_banner()

    def _on_history_reversal_finished(
        self,
    ):
        if self._reversal_thread is not None:
            self._reversal_thread.deleteLater()
            self._reversal_thread = None

        self._reversal_in_progress = False

        self._set_navigation_enabled(
            True
        )

        if (
            self._reversal_reload_after_applied_failure
        ):
            self._reversal_reload_after_applied_failure = (
                False
            )

            self._start_workspace_load()
            return

        self.pages.setEnabled(
            True
        )

        self._update_workspace_banner()

        page = (
            self.pages.currentWidget()
        )

        if hasattr(
            page,
            "ensure_loaded",
        ):
            page.ensure_loaded()

    def _start_presupuesto_save(
        self,
        actor: str,
    ):
        if (
            self._save_thread is not None
            and self._save_thread.isRunning()
        ):
            return

        if not self.workspace.has_changes:
            return

        self._save_in_progress = True
        self._reload_after_applied_failure = False

        self.pages.setEnabled(
            False
        )

        self.workspace_banner.setText(
            f"{self.active_module.label}  |  "
            "Guardando cambios "
            "en BigQuery..."
        )

        self._update_apply_button(
            self.workspace.pending_row_count
        )

        self._save_thread = (
            PresupuestoSaveThread(
                workspace=self.workspace,
                actor=actor,
                parent=self,
            )
        )

        self._save_thread.completed.connect(
            self._on_presupuesto_save_completed
        )

        self._save_thread.failed.connect(
            self._on_presupuesto_save_failed
        )

        self._save_thread.finished.connect(
            self._on_presupuesto_save_finished
        )

        self._save_thread.start()

    def _on_presupuesto_save_completed(
        self,
        outcome,
    ):
        result = (
            outcome.persistence_result
        )

        self._invalidate_page(
            self.history_page
        )

        if result.status == "APPLIED":
            self._invalidate_page(
                self.dashboard_page
            )

            self._invalidate_page(
                self.presupuesto_page
            )

            self._invalidate_page(
                self.aggregation_page
            )

            self.dashboard_page.set_workspace_ready()
            self.presupuesto_page.set_workspace_ready()
            self.aggregation_page.set_workspace_ready()

            self._update_workspace_banner()

            page = self.pages.currentWidget()

            if hasattr(
                page,
                "ensure_loaded",
            ):
                page.ensure_loaded()

            show_info(
                self,
                "Cambios aplicados",
                f"Los cambios {self.active_module.label} "
                "se guardaron correctamente "
                "en BigQuery.\n\n"
                f"Filas actualizadas: "
                f"{result.row_count:,}\n"
                f"Campos modificados: "
                f"{result.field_count:,}\n"
                f"Batch: {result.batch_id}",
            )

            return

        if result.status == "CONFLICT":
            conflicts = (
                result.conflicts
            )

            preview_lines = []

            for conflict in conflicts[:5]:
                current = (
                    conflict.current_version
                    if conflict.current_version
                    is not None
                    else "no encontrada"
                )

                preview_lines.append(
                    f"- {conflict.row_id}: "
                    f"version esperada "
                    f"{conflict.expected_version}, "
                    f"actual {current}"
                )

            preview = "\n".join(
                preview_lines
            )

            if len(conflicts) > 5:
                preview += "\n- ..."

            show_warning(
                self,
                "Conflicto de versiones",
                "No se aplico ningun cambio.\n\n"
                "Otra sesion modifico una o "
                "mas filas desde que cargaste "
                "el presupuesto.\n\n"
                f"Conflictos: "
                f"{len(conflicts):,}\n\n"
                f"{preview}\n\n"
                "Tus cambios locales se "
                "mantienen intactos.",
            )

            self._update_workspace_banner()
            return

        if result.status == "FAILED":
            show_error(
                self,
                "No se pudieron aplicar los cambios",
                "BigQuery rechazo o revirtio "
                "la operacion.\n\n"
                "No se modifico el Workspace "
                "local.\n\n"
                f"Detalle: "
                f"{result.error_message}",
            )

            self._update_workspace_banner()
            return

        show_warning(
            self,
            "Resultado no reconocido",
            "La operacion termino con un "
            "estado inesperado:\n\n"
            f"{result.status}",
        )

    def _on_presupuesto_save_failed(
        self,
        failure,
    ):
        if failure.was_applied:
            self._reload_after_applied_failure = True

            self._invalidate_page(
                self.history_page
            )

            self.workspace_banner.setText(
                f"{self.active_module.label}  |  "
                "Cambios guardados en BigQuery  |  "
                "Recarga pendiente"
            )

            show_warning(
                self,
                "Cambios guardados, recarga pendiente",
                "Los cambios SI fueron aplicados "
                "en BigQuery, pero fallo la "
                "recarga del Workspace.\n\n"
                "No vuelvas a aplicar los mismos "
                "cambios.\n\n"
                "La aplicacion intentara recargar "
                "el presupuesto nuevamente.",
            )

            return

        show_error(
            self,
            "Error al guardar cambios",
            "No se pudo confirmar el guardado "
            "de los cambios.\n\n"
            "Tus cambios locales se mantienen "
            "intactos.\n\n"
            f"Detalle: {failure.message}",
        )

        self._update_workspace_banner()

    def _on_presupuesto_save_finished(
        self,
    ):
        if self._save_thread is not None:
            self._save_thread.deleteLater()
            self._save_thread = None

        self._save_in_progress = False

        if self._reload_after_applied_failure:
            self._reload_after_applied_failure = False

            self._start_workspace_load()
            return

        self.pages.setEnabled(
            True
        )

        self._update_workspace_banner()

    def _on_workspace_failed(
        self,
        message: str,
    ):
        self.pages.setEnabled(
            False
        )

        self.workspace_banner.setText(
            "ERROR AL CARGAR PRESUPUESTO  |  "
            + message
        )

        self._update_apply_button(
            0
        )

        self.dashboard_page.set_workspace_error(
            message
        )

        self.presupuesto_page.set_workspace_error(
            message
        )

        self.aggregation_page.set_workspace_error(
            message
        )

    def _on_workspace_finished(self):
        if self._workspace_loader is not None:
            self._workspace_loader.deleteLater()
            self._workspace_loader = None