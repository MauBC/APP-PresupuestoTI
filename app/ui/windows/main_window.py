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
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import settings
from app.services.presupuesto_change_summary_service import (
    PresupuestoChangeSummaryService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_analysis_service import (
    PresupuestoWorkspaceAnalysisService,
)
from app.ui.dialogs.apply_changes_dialog import (
    ApplyChangesDialog,
)
from app.ui.pages.aggregation_page import (
    AggregationPage,
)
from app.ui.pages.dashboard_page import (
    DashboardPage,
)
from app.ui.pages.presupuesto_page import (
    PresupuestoPage,
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

        self.workspace = (
            PresupuestoWorkspace()
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
            "Preparando simulacion local..."
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
        layout.addSpacing(26)

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

        layout.addWidget(
            dashboard_button
        )

        layout.addWidget(
            presupuesto_button
        )

        layout.addWidget(
            aggregation_button
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

        self.workspace_banner.setText(
            "Cargando presupuesto desde "
            "BigQuery para trabajar en modo local..."
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
            "MODO SIMULACION LOCAL  |  "
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

        text += (
            "  |  BigQuery sin cambios"
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
        if not self.workspace.is_loaded:
            QMessageBox.information(
                self,
                "Aplicar cambios",
                "El presupuesto todavia "
                "no se encuentra cargado.",
            )
            return

        if not self.workspace.has_changes:
            QMessageBox.information(
                self,
                "Aplicar cambios",
                "No existen cambios pendientes.",
            )
            return

        try:
            summary = (
                self.change_summary_service
                .build()
            )

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Aplicar cambios",
                "No se pudo preparar el "
                "resumen de cambios.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        dialog = ApplyChangesDialog(
            summary,
            self,
        )

        if not dialog.exec():
            return

        self._show_demo_confirmation()

    def _show_demo_confirmation(self):
        from PySide6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
        )

        dialog = QDialog(self)

        dialog.setObjectName(
            "confirmationReceivedDialog"
        )

        dialog.setWindowTitle(
            "Confirmacion recibida"
        )

        dialog.setFixedWidth(
            460
        )

        dialog.setStyleSheet(
            """
            QDialog#confirmationReceivedDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QDialog#confirmationReceivedDialog QLabel {
                background-color: transparent;
                color: #1F2937;
            }

            QLabel#confirmationTitle {
                font-size: 19px;
                font-weight: 700;
                color: #1F2937;
            }

            QLabel#confirmationMessage {
                font-size: 13px;
                color: #344054;
                line-height: 1.4;
            }

            QLabel#confirmationNotice {
                background-color: #EEF4FF;
                color: #3538CD;
                border: 1px solid #C7D7FE;
                border-radius: 7px;
                padding: 11px;
                font-weight: 600;
            }

            QDialogButtonBox QPushButton {
                background-color: #2F7650;
                color: #FFFFFF;
                border: 1px solid #2F7650;
                border-radius: 6px;
                padding: 8px 22px;
                min-width: 90px;
                font-weight: 600;
            }

            QDialogButtonBox QPushButton:hover {
                background-color: #285F42;
            }
            """
        )

        layout = QVBoxLayout(dialog)

        layout.setContentsMargins(
            28,
            24,
            28,
            24,
        )

        layout.setSpacing(
            16
        )

        title = QLabel(
            "Confirmacion recibida"
        )

        title.setObjectName(
            "confirmationTitle"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            title
        )

        message = QLabel(
            "La confirmacion fue aceptada "
            "correctamente."
        )

        message.setObjectName(
            "confirmationMessage"
        )

        message.setWordWrap(
            True
        )

        message.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            message
        )

        notice = QLabel(
            "Esta funcionalidad todavia se "
            "encuentra en modo demostracion.\n\n"
            "NO se realizo ningun cambio "
            "en BigQuery."
        )

        notice.setObjectName(
            "confirmationNotice"
        )

        notice.setWordWrap(
            True
        )

        notice.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            notice
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
        )

        ok_button = buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )

        ok_button.setText(
            "Entendido"
        )

        buttons.accepted.connect(
            dialog.accept
        )

        layout.addWidget(
            buttons,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        dialog.exec()

    def _on_workspace_failed(
        self,
        message: str,
    ):
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