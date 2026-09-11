
from pathlib import Path

from PySide6.QtCore import (
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.models.budget_excel_import import (
    BudgetImportIssueSeverity,
)
from app.ui.models.budget_import_preview_model import (
    BudgetImportIssueModel,
    BudgetImportPreviewModel,
)


class BudgetExcelImportDialog(
    QDialog
):
    def __init__(
        self,
        *,
        result,
        module_config,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._result = (
            result
        )

        self._config = (
            module_config
        )

        self._models = []
        self._proxies = []

        self.setObjectName(
            "budgetExcelImportDialog"
        )

        self.setWindowTitle(
            "Importar Excel "
            f"{module_config.label}"
        )

        self.resize(
            1380,
            780,
        )

        self.setMinimumSize(
            1050,
            620,
        )

        self._apply_style()
        self._setup_ui()

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#budgetExcelImportDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QLabel {
                color: #1F2937;
            }

            QLabel#importTitle {
                font-size: 21px;
                font-weight: 700;
            }

            QLabel#importSubtitle {
                color: #667085;
                font-size: 12px;
            }

            QLabel#importBlocked {
                background-color: #FEF3F2;
                color: #B42318;
                border: 1px solid #FECDCA;
                border-radius: 6px;
                padding: 9px;
                font-weight: 700;
            }

            QLabel#importValid {
                background-color: #ECFDF3;
                color: #067647;
                border: 1px solid #ABEFC6;
                border-radius: 6px;
                padding: 9px;
                font-weight: 700;
            }

            QFrame#importCard {
                background-color: #F3F4F6;
                border: 1px solid #D8DEE4;
                border-radius: 8px;
            }

            QLabel#importCardTitle {
                color: #667085;
                font-size: 11px;
                font-weight: 600;
            }

            QLabel#importCardValue {
                color: #111827;
                font-size: 17px;
                font-weight: 700;
            }

            QLineEdit {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #98A2B3;
                border-radius: 6px;
                padding: 8px;
            }

            QLineEdit:focus {
                border: 2px solid #2F7650;
            }

            QTableView {
                background-color: #FFFFFF;
                alternate-background-color: #F8F9FA;
                gridline-color: #E5E7EB;
                color: #1F2937;
                selection-background-color: #DCEFE4;
                selection-color: #1F2937;
            }

            QHeaderView::section {
                background-color: #EEF1F4;
                color: #344054;
                padding: 7px;
                border: 0px;
                border-right: 1px solid #D8DEE4;
                border-bottom: 1px solid #D8DEE4;
                font-weight: 600;
            }

            QTabWidget::pane {
                border: 1px solid #D8DEE4;
                background-color: #FFFFFF;
            }

            QTabBar::tab {
                background-color: #EEF1F4;
                color: #344054;
                padding: 9px 18px;
                border: 1px solid #D8DEE4;
            }

            QTabBar::tab:selected {
                background-color: #FFFFFF;
                color: #2F7650;
                font-weight: 700;
                border-bottom: 2px solid #2F7650;
            }

            QPushButton {
                background-color: #F2F4F7;
                color: #1F2937;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 9px 18px;
                min-width: 110px;
            }

            QPushButton:hover {
                border-color: #2F7650;
                color: #2F7650;
            }

            QPushButton#importButton {
                background-color: #2F7650;
                color: #FFFFFF;
                border-color: #2F7650;
                font-weight: 700;
            }

            QPushButton#importButton:hover {
                background-color: #285F42;
            }

            QPushButton#importButton:disabled {
                background-color: #D0D5DD;
                color: #667085;
                border-color: #D0D5DD;
            }
            """
        )

    def _setup_ui(
        self,
    ):
        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            24,
            22,
            24,
            22,
        )

        layout.setSpacing(
            13
        )

        title = QLabel(
            "Importar Excel "
            f"{self._config.label}"
        )

        title.setObjectName(
            "importTitle"
        )

        source_name = (
            Path(
                self._result
                .source_path
            )
            .name
        )

        subtitle = QLabel(
            f"Archivo: {source_name}  |  "
            f"Hoja: {self._result.sheet_name}\n"
            "La validacion es local. "
            "BigQuery todavia no sera modificado."
        )

        subtitle.setObjectName(
            "importSubtitle"
        )

        subtitle.setWordWrap(
            True
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        layout.addLayout(
            self._build_cards()
        )

        status = QLabel()

        status.setWordWrap(
            True
        )

        if self._result.is_valid:
            status.setObjectName(
                "importValid"
            )

            status.setText(
                "Archivo valido. "
                f"{self._result.importable_count:,} "
                "filas pueden agregarse "
                "al Workspace."
            )

        else:
            status.setObjectName(
                "importBlocked"
            )

            status.setText(
                "Importacion bloqueada. "
                "Corrige los errores del "
                "archivo antes de continuar. "
                "No se agregara ninguna fila."
            )

        layout.addWidget(
            status
        )

        tabs = QTabWidget()

        if self._result.rows:
            tabs.addTab(
                self._build_preview_tab(),
                "PREVIEW "
                f"({self._result.importable_count:,})",
            )

        error_issues = (
            self._issues(
                BudgetImportIssueSeverity
                .ERROR
            )
        )

        warning_issues = (
            self._issues(
                BudgetImportIssueSeverity
                .WARNING
            )
        )

        info_issues = (
            self._issues(
                BudgetImportIssueSeverity
                .INFO
            )
        )

        if error_issues:
            tabs.addTab(
                self._build_issue_tab(
                    error_issues
                ),
                "ERRORES "
                f"({len(error_issues):,})",
            )

        if warning_issues:
            tabs.addTab(
                self._build_issue_tab(
                    warning_issues
                ),
                "ADVERTENCIAS "
                f"({len(warning_issues):,})",
            )

        if info_issues:
            tabs.addTab(
                self._build_issue_tab(
                    info_issues
                ),
                "INFORMATIVOS "
                f"({len(info_issues):,})",
            )

        layout.addWidget(
            tabs,
            1,
        )

        buttons = QHBoxLayout()

        buttons.addStretch()

        cancel_button = QPushButton(
            "Cancelar"
        )

        import_button = QPushButton(
            "Agregar "
            f"{self._result.importable_count:,} "
            "filas"
        )

        import_button.setObjectName(
            "importButton"
        )

        import_button.setEnabled(
            self._result.is_valid
        )

        cancel_button.clicked.connect(
            self.reject
        )

        import_button.clicked.connect(
            self.accept
        )

        buttons.addWidget(
            cancel_button
        )

        buttons.addWidget(
            import_button
        )

        layout.addLayout(
            buttons
        )

    def _build_cards(
        self,
    ):
        layout = QHBoxLayout()

        cards = (
            (
                "FILAS LEIDAS",
                self._result
                .rows_read,
            ),
            (
                "IMPORTABLES",
                self._result
                .importable_count,
            ),
            (
                "ERRORES",
                self._result
                .error_count,
            ),
            (
                "ADVERTENCIAS",
                self._result
                .warning_count,
            ),
            (
                "INFORMATIVOS",
                self._result
                .info_count,
            ),
        )

        for title, value in cards:
            card = QFrame()

            card.setObjectName(
                "importCard"
            )

            card_layout = (
                QVBoxLayout(
                    card
                )
            )

            card_layout.setContentsMargins(
                13,
                9,
                13,
                9,
            )

            label = QLabel(
                title
            )

            label.setObjectName(
                "importCardTitle"
            )

            number = QLabel(
                f"{value:,}"
            )

            number.setObjectName(
                "importCardValue"
            )

            card_layout.addWidget(
                label
            )

            card_layout.addWidget(
                number
            )

            layout.addWidget(
                card
            )

        return layout

    def _build_preview_tab(
        self,
    ):
        widget = QWidget()

        layout = QVBoxLayout(
            widget
        )

        layout.setContentsMargins(
            10,
            10,
            10,
            10,
        )

        search = QLineEdit()

        search.setPlaceholderText(
            "Buscar dentro del preview..."
        )

        model = (
            BudgetImportPreviewModel(
                rows=(
                    self._result.rows
                ),
                module_config=(
                    self._config
                ),
                parent=self,
            )
        )

        proxy = (
            QSortFilterProxyModel(
                self
            )
        )

        proxy.setSourceModel(
            model
        )

        proxy.setFilterKeyColumn(
            -1
        )

        proxy.setFilterCaseSensitivity(
            Qt.CaseSensitivity
            .CaseInsensitive
        )

        proxy.setSortRole(
            Qt.ItemDataRole
            .UserRole
        )

        table = QTableView()

        table.setModel(
            proxy
        )

        self._prepare_table(
            table
        )

        table.setSortingEnabled(
            True
        )

        search.textChanged.connect(
            proxy
            .setFilterFixedString
        )

        self._models.append(
            model
        )

        self._proxies.append(
            proxy
        )

        layout.addWidget(
            search
        )

        layout.addWidget(
            table,
            1,
        )

        return widget

    def _build_issue_tab(
        self,
        issues,
    ):
        widget = QWidget()

        layout = QVBoxLayout(
            widget
        )

        layout.setContentsMargins(
            10,
            10,
            10,
            10,
        )

        search = QLineEdit()

        search.setPlaceholderText(
            "Buscar fila, codigo, "
            "columna o detalle..."
        )

        model = (
            BudgetImportIssueModel(
                issues=issues,
                parent=self,
            )
        )

        proxy = (
            QSortFilterProxyModel(
                self
            )
        )

        proxy.setSourceModel(
            model
        )

        proxy.setFilterKeyColumn(
            -1
        )

        proxy.setFilterCaseSensitivity(
            Qt.CaseSensitivity
            .CaseInsensitive
        )

        table = QTableView()

        table.setModel(
            proxy
        )

        self._prepare_table(
            table
        )

        search.textChanged.connect(
            proxy
            .setFilterFixedString
        )

        self._models.append(
            model
        )

        self._proxies.append(
            proxy
        )

        layout.addWidget(
            search
        )

        layout.addWidget(
            table,
            1,
        )

        return widget

    @staticmethod
    def _prepare_table(
        table,
    ):
        table.setAlternatingRowColors(
            True
        )

        table.setSelectionBehavior(
            QAbstractItemView
            .SelectionBehavior
            .SelectRows
        )

        table.setSelectionMode(
            QAbstractItemView
            .SelectionMode
            .ExtendedSelection
        )

        table.setEditTriggers(
            QAbstractItemView
            .EditTrigger
            .NoEditTriggers
        )

        table.setHorizontalScrollMode(
            QAbstractItemView
            .ScrollMode
            .ScrollPerPixel
        )

        table.setVerticalScrollMode(
            QAbstractItemView
            .ScrollMode
            .ScrollPerPixel
        )

        table.verticalHeader().setVisible(
            False
        )

        header = (
            table.horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView
            .ResizeMode
            .Interactive
        )

        header.setDefaultSectionSize(
            150
        )

        header.setMinimumSectionSize(
            80
        )

    def _issues(
        self,
        severity,
    ):
        return tuple(
            issue
            for issue in (
                self._result
                .issues
            )
            if (
                issue.severity
                == severity
            )
        )
