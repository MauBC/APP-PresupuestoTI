
from pathlib import Path

from PySide6.QtCore import (
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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

from app.ui.dialogs.app_message_box import (
    ask_text_input,
)
from app.models.budget_excel_import import (
    BudgetImportIssueSeverity,
)
from app.ui.models.budget_import_preview_model import (
    BudgetImportIssueFilterProxyModel,
    BudgetImportIssueModel,
    BudgetImportPreviewModel,
    format_import_value,
)


class BudgetExcelImportDialog(
    QDialog
):
    REVALIDATE_CODE = 1001

    def __init__(
        self,
        *,
        result,
        module_config,
        corrections=None,
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

        self._corrections = dict(
            corrections
            or {}
        )

        self._models = []
        self._proxies = []

        self._issue_model = None
        self._issue_proxy = None
        self._issue_table = None
        self._issue_edit_button = None

        self._preview_model = None
        self._preview_proxy = None
        self._preview_table = None
        self._preview_selection_label = None
        self._status_label = None
        self._import_button = None

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

        self._status_label = (
            status
        )

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

        self._import_button = (
            import_button
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

        self._update_import_selection()

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
            (
                "IGNORADAS",
                self._result
                .ignored_row_count,
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

        controls = QHBoxLayout()

        search = QLineEdit()

        search.setPlaceholderText(
            "Buscar dentro del preview..."
        )

        include_all_button = (
            QPushButton(
                "Incluir todas"
            )
        )

        exclude_button = (
            QPushButton(
                "Excluir seleccionadas"
            )
        )

        selection_label = QLabel()

        self._preview_selection_label = (
            selection_label
        )

        model = (
            BudgetImportPreviewModel(
                rows=(
                    self._result.rows
                ),
                module_config=(
                    self._config
                ),
                source_row_numbers=(
                    self._result
                    .source_row_numbers
                ),
                parent=self,
            )
        )

        self._preview_model = (
            model
        )

        proxy = (
            QSortFilterProxyModel(
                self
            )
        )

        self._preview_proxy = (
            proxy
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

        self._preview_table = (
            table
        )

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

        include_all_button.clicked.connect(
            self._include_all_preview_rows
        )

        exclude_button.clicked.connect(
            self._exclude_selected_preview_rows
        )

        model.dataChanged.connect(
            self._update_import_selection
        )

        self._models.append(
            model
        )

        self._proxies.append(
            proxy
        )

        controls.addWidget(
            search,
            1,
        )

        controls.addWidget(
            include_all_button
        )

        controls.addWidget(
            exclude_button
        )

        controls.addWidget(
            selection_label
        )

        layout.addLayout(
            controls
        )

        layout.addWidget(
            table,
            1,
        )

        self._update_import_selection()

        return widget

    def rows_to_import(
        self,
    ):
        if (
            self._preview_model
            is None
        ):
            return tuple(
                self._result.rows
            )

        return (
            self._preview_model
            .included_rows()
        )

    def _include_all_preview_rows(
        self,
    ):
        if (
            self._preview_model
            is None
        ):
            return

        self._preview_model.include_all()

        self._update_import_selection()

    def _exclude_selected_preview_rows(
        self,
    ):
        if (
            self._preview_model
            is None
            or
            self._preview_proxy
            is None
            or
            self._preview_table
            is None
        ):
            return

        selection = (
            self._preview_table
            .selectionModel()
        )

        if selection is None:
            return

        source_rows = set()

        for proxy_index in (
            selection.selectedRows()
        ):
            source_index = (
                self._preview_proxy
                .mapToSource(
                    proxy_index
                )
            )

            if (
                source_index
                .isValid()
            ):
                source_rows.add(
                    source_index.row()
                )

        for row_index in (
            source_rows
        ):
            self._preview_model.set_included(
                row_index,
                False,
            )

        self._update_import_selection()

    def _update_import_selection(
        self,
        *_,
    ):
        included = (
            self._result
            .importable_count
        )

        excluded = 0

        if (
            self._preview_model
            is not None
        ):
            included = (
                self._preview_model
                .included_count
            )

            excluded = (
                self._preview_model
                .excluded_count
            )

        if (
            self._preview_selection_label
            is not None
        ):
            self._preview_selection_label.setText(
                f"Incluidas: "
                f"{included:,} | "
                f"Excluidas: "
                f"{excluded:,}"
            )

        if (
            self._import_button
            is not None
        ):
            self._import_button.setText(
                "Agregar "
                f"{included:,} filas"
            )

            self._import_button.setEnabled(
                bool(
                    self._result.is_valid
                    and included > 0
                )
            )

        if (
            self._status_label
            is not None
            and self._result.is_valid
        ):
            self._status_label.setText(
                "Archivo valido. "
                f"{included:,} filas "
                "estan seleccionadas "
                "para agregarse "
                "al Workspace."
            )

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

        controls = QHBoxLayout()

        search = QLineEdit()

        search.setPlaceholderText(
            "Buscar fila, contexto, codigo, "
            "columna o detalle..."
        )

        severity = QComboBox()

        severity.addItem(
            "Todos",
            None,
        )

        severity.addItem(
            "Errores",
            "ERROR",
        )

        severity.addItem(
            "Advertencias",
            "WARNING",
        )

        severity.addItem(
            "Informativos",
            "INFO",
        )

        edit_button = QPushButton(
            "Corregir valor seleccionado"
        )

        edit_button.setEnabled(
            False
        )

        model = (
            BudgetImportIssueModel(
                issues=issues,
                parent=self,
            )
        )

        self._issue_model = (
            model
        )

        proxy = (
            BudgetImportIssueFilterProxyModel(
                self
            )
        )

        self._issue_proxy = (
            proxy
        )

        proxy.setSourceModel(
            model
        )

        table = QTableView()

        self._issue_table = (
            table
        )

        self._issue_edit_button = (
            edit_button
        )

        table.setModel(
            proxy
        )

        self._prepare_table(
            table
        )

        search.textChanged.connect(
            proxy.set_search_text
        )

        severity.currentIndexChanged.connect(
            lambda _:
                proxy.set_severity(
                    severity.currentData()
                )
        )

        edit_button.clicked.connect(
            self._edit_selected_issue
        )

        selection = (
            table.selectionModel()
        )

        if selection is not None:
            selection.selectionChanged.connect(
                self._update_issue_edit_button
            )

        self._models.append(
            model
        )

        self._proxies.append(
            proxy
        )

        controls.addWidget(
            search,
            1,
        )

        controls.addWidget(
            severity
        )

        controls.addWidget(
            edit_button
        )

        layout.addLayout(
            controls
        )

        layout.addWidget(
            table,
            1,
        )

        return widget

    def corrections(
        self,
    ):
        return dict(
            self._corrections
        )

    def _selected_issue(
        self,
    ):
        if (
            self._issue_table
            is None
            or self._issue_proxy
            is None
            or self._issue_model
            is None
        ):
            return None

        index = (
            self._issue_table
            .currentIndex()
        )

        if not index.isValid():
            return None

        source_index = (
            self._issue_proxy
            .mapToSource(
                index
            )
        )

        if not source_index.isValid():
            return None

        return (
            self._issue_model
            .issue_at(
                source_index.row()
            )
        )

    def _issue_can_be_corrected(
        self,
        issue,
    ):
        if issue is None:
            return False

        if (
            issue.severity
            != BudgetImportIssueSeverity.ERROR
            and
            getattr(
                issue,
                "expected_value",
                None,
            )
            is None
        ):
            return False

        if (
            issue.row_number
            < 2
        ):
            return False

        return (
            issue.column
            in self._config
            .insert_columns
        )

    def _update_issue_edit_button(
        self,
        *_,
    ):
        if (
            self._issue_edit_button
            is None
        ):
            return

        self._issue_edit_button.setEnabled(
            self._issue_can_be_corrected(
                self._selected_issue()
            )
        )

    def _edit_selected_issue(
        self,
    ):
        issue = (
            self._selected_issue()
        )

        if not (
            self._issue_can_be_corrected(
                issue
            )
        ):
            return

        key = (
            issue.row_number,
            issue.column,
        )

        expected = getattr(
            issue,
            "expected_value",
            None,
        )

        if key in self._corrections:
            initial_value = (
                self._corrections[
                    key
                ]
            )

        elif expected is not None:
            initial_value = (
                format_import_value(
                    expected
                )
                .replace(
                    ",",
                    "",
                )
            )

        else:
            initial_value = (
                ""
                if issue.raw_value is None
                else str(
                    issue.raw_value
                )
            )

        context = (
            issue.context
            or
            "Sin contexto de negocio disponible."
        )

        labels = {
            "anio_ml":
                "TOTAL ML",
            "anio_usd":
                "TOTAL USD",
        }

        column_label = (
            labels.get(
                issue.column,
                str(
                    issue.column
                )
                .replace(
                    "_",
                    " ",
                )
                .upper(),
            )
        )

        message = (
            f"Fila Excel: "
            f"{issue.row_number}\n"
            f"{context}\n\n"
            f"Columna: "
            f"{column_label}\n"
            f"Valor actual: "
            f"{format_import_value(issue.raw_value)}\n"
            f"Detalle: "
            f"{issue.message}"
        )

        if (
            issue.column
            in {
                "anio_ml",
                "anio_usd",
            }
            and expected is not None
        ):
            message += (
                "\n\n"
                "El valor esperado fue "
                "calculado automaticamente "
                "como la suma de los "
                "12 meses."
            )

        expected_text = (
            None
            if expected is None
            else format_import_value(
                expected
            )
        )

        value, accepted = (
            ask_text_input(
                self,
                "Corregir valor de importacion",
                message,
                initial_value=(
                    initial_value
                ),
                expected_value=(
                    expected_text
                ),
                confirm_text=(
                    "Aplicar correccion"
                ),
                cancel_text="Cancelar",
            )
        )

        if not accepted:
            return

        self._corrections[
            key
        ] = value

        self.done(
            self.REVALIDATE_CODE
        )

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
