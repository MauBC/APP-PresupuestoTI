from decimal import Decimal

from PySide6.QtGui import (
    QBrush,
    QColor,
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


ZERO = Decimal("0.00")


class ChangeSummaryDialog(QDialog):
    MAX_DETAILS = 5000

    def __init__(
        self,
        summary,
        parent=None,
        *,
        module_label: str = "OPEX",
    ):
        super().__init__(
            parent
        )

        self._summary = summary
        self._module_label = (
            module_label
        )

        self.setObjectName(
            "changeSummaryDialog"
        )

        self.setWindowTitle(
            "Cambios pendientes "
            f"{module_label}"
        )

        self.resize(
            1380,
            760,
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
            QDialog#changeSummaryDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QDialog#changeSummaryDialog QLabel {
                background-color: transparent;
                color: #1F2937;
            }

            QFrame#summaryCard {
                background-color: #F3F4F6;
                border: 1px solid #D8DEE4;
                border-radius: 8px;
            }

            QLabel#cardTitle {
                color: #667085;
                font-size: 11px;
                font-weight: 600;
            }

            QLabel#cardValue {
                color: #111827;
                font-size: 17px;
                font-weight: 700;
            }

            QLabel#summaryTitle {
                font-size: 21px;
                font-weight: 700;
                color: #1F2937;
            }

            QLabel#summarySubtitle {
                color: #667085;
                font-size: 12px;
            }

            QLabel#detailWarning {
                background-color: #FFF4E5;
                color: #92400E;
                border: 1px solid #F3D3A3;
                border-radius: 6px;
                padding: 8px;
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
                min-width: 150px;
            }

            QTabBar::tab:selected {
                background-color: #FFFFFF;
                color: #2F7650;
                font-weight: 700;
                border-bottom: 2px solid #2F7650;
            }

            QLineEdit {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #98A2B3;
                border-radius: 6px;
                padding: 8px 10px;
            }

            QLineEdit:focus {
                border: 2px solid #2F7650;
            }

            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F8F9FA;
                color: #1F2937;
                gridline-color: #E5E7EB;
                selection-background-color: #DCEFE4;
                selection-color: #1F2937;
            }

            QHeaderView::section {
                background-color: #EEF1F4;
                color: #344054;
                border: 0px;
                border-right: 1px solid #D8DEE4;
                border-bottom: 1px solid #D8DEE4;
                padding: 7px;
                font-weight: 600;
            }

            QPushButton {
                background-color: #F2F4F7;
                color: #1F2937;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 8px 18px;
                min-width: 110px;
            }

            QPushButton:hover {
                border-color: #2F7650;
                color: #2F7650;
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
            14
        )

        title = QLabel(
            "Cambios pendientes "
            f"{self._module_label}"
        )

        title.setObjectName(
            "summaryTitle"
        )

        subtitle = QLabel(
            "Revisa el impacto de las "
            "modificaciones antes de "
            "aplicarlas en BigQuery."
        )

        subtitle.setObjectName(
            "summarySubtitle"
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        layout.addLayout(
            self._build_summary_cards()
        )

        self.tabs = QTabWidget()

        if self._summary.by_country:
            self.tabs.addTab(
                self._build_breakdown_tab(
                    self._summary.by_country,
                    "PAIS",
                ),
                "POR PAIS",
            )

        if self._summary.by_budgeter:
            self.tabs.addTab(
                self._build_breakdown_tab(
                    self._summary.by_budgeter,
                    "PRESUPUESTADOR",
                ),
                "POR PRESUPUESTADOR",
            )

        self.tabs.addTab(
            self._build_detail_tab(),
            "DETALLE",
        )

        layout.addWidget(
            self.tabs,
            1,
        )

        buttons = QHBoxLayout()

        buttons.addStretch()

        close_button = QPushButton(
            "Cerrar"
        )

        close_button.clicked.connect(
            self.accept
        )

        buttons.addWidget(
            close_button
        )

        layout.addLayout(
            buttons
        )

    def _build_summary_cards(
        self,
    ):
        layout = QHBoxLayout()

        values = (
            (
                "FILAS MODIFICADAS",
                f"{self._summary.pending_rows:,}",
            ),
            (
                "CAMPOS MODIFICADOS",
                f"{self._summary.pending_fields:,}",
            ),
            (
                "PRESUPUESTO ORIGINAL",
                self._format_money(
                    self._summary.original_total
                ),
            ),
            (
                "PRESUPUESTO MODIFICADO",
                self._format_money(
                    self._summary.simulated_total
                ),
            ),
            (
                "VARIACION TOTAL",
                self._format_difference(
                    self._summary.difference
                ),
            ),
        )

        for (
            title,
            value,
        ) in values:
            card = QFrame()

            card.setObjectName(
                "summaryCard"
            )

            card_layout = (
                QVBoxLayout(
                    card
                )
            )

            card_layout.setContentsMargins(
                13,
                10,
                13,
                10,
            )

            card_title = QLabel(
                title
            )

            card_title.setObjectName(
                "cardTitle"
            )

            card_value = QLabel(
                value
            )

            card_value.setObjectName(
                "cardValue"
            )

            if (
                title
                == "VARIACION TOTAL"
            ):
                card_value.setStyleSheet(
                    self._variation_style(
                        self._summary
                        .difference
                    )
                )

            card_layout.addWidget(
                card_title
            )

            card_layout.addWidget(
                card_value
            )

            layout.addWidget(
                card
            )

        return layout

    def _build_breakdown_tab(
        self,
        rows,
        key_header,
    ):
        widget = QWidget()

        layout = QVBoxLayout(
            widget
        )

        layout.setContentsMargins(
            10,
            12,
            10,
            10,
        )

        layout.setSpacing(
            10
        )

        table = QTableWidget(
            len(rows),
            5,
        )

        table.setHorizontalHeaderLabels(
            [
                key_header,
                "ORIGINAL",
                "MODIFICADO",
                "VARIACION",
                "VARIACION %",
            ]
        )

        self._prepare_table(
            table
        )

        for (
            row_index,
            row,
        ) in enumerate(rows):
            values = (
                row.key,
                self._format_money(
                    row.original_total
                ),
                self._format_money(
                    row.simulated_total
                ),
                self._format_difference(
                    row.difference
                ),
                self._format_percent(
                    row.variation_percent
                ),
            )

            for (
                column_index,
                value,
            ) in enumerate(values):
                item = QTableWidgetItem(
                    str(value)
                )

                if column_index in (
                    3,
                    4,
                ):
                    self._color_variation_item(
                        item,
                        row.difference,
                    )

                table.setItem(
                    row_index,
                    column_index,
                    item,
                )

        header = (
            table.horizontalHeader()
        )

        header.setSectionResizeMode(
            0,
            QHeaderView
            .ResizeMode
            .Stretch,
        )

        for index in range(
            1,
            5,
        ):
            header.setSectionResizeMode(
                index,
                QHeaderView
                .ResizeMode
                .ResizeToContents,
            )

        layout.addWidget(
            table
        )

        return widget

    def _build_detail_tab(
        self,
    ):
        widget = QWidget()

        layout = QVBoxLayout(
            widget
        )

        layout.setContentsMargins(
            10,
            12,
            10,
            10,
        )

        layout.setSpacing(
            9
        )

        search_layout = QHBoxLayout()

        search_label = QLabel(
            "Buscar:"
        )

        self.detail_search = (
            QLineEdit()
        )

        self.detail_search.setPlaceholderText(
            "Proveedor, CECO, compania, "
            "gasto, pais, presupuestador..."
        )

        search_layout.addWidget(
            search_label
        )

        search_layout.addWidget(
            self.detail_search,
            1,
        )

        layout.addLayout(
            search_layout
        )

        all_details = tuple(
            self._summary.details
        )

        visible_details = (
            all_details[
                :self.MAX_DETAILS
            ]
        )

        if (
            len(all_details)
            > self.MAX_DETAILS
        ):
            warning = QLabel(
                "La vista se limita a los "
                f"primeros "
                f"{self.MAX_DETAILS:,} "
                "cambios."
            )

            warning.setObjectName(
                "detailWarning"
            )

            layout.addWidget(
                warning
            )

        context_columns = (
            self._context_columns(
                visible_details
            )
        )

        headers = [
            *(
                label.upper()
                for _, label
                in context_columns
            ),
            "CAMPO",
            "ANTES",
            "AHORA",
            "VARIACION",
            "VARIACION %",
        ]

        self.detail_table = (
            QTableWidget(
                len(
                    visible_details
                ),
                len(
                    headers
                ),
            )
        )

        self.detail_table.setHorizontalHeaderLabels(
            headers
        )

        self._prepare_table(
            self.detail_table
        )

        for (
            row_index,
            detail,
        ) in enumerate(
            visible_details
        ):
            context_map = (
                detail.context_map
            )

            values = []

            for (
                column,
                _,
            ) in context_columns:
                values.append(
                    context_map.get(
                        column,
                        "(Sin valor)",
                    )
                )

            values.extend(
                (
                    self._field_label(
                        detail.column
                    ),
                    self._format_value(
                        detail.before
                    ),
                    self._format_value(
                        detail.after
                    ),
                    self._format_difference(
                        detail.difference
                    ),
                    self._format_percent(
                        detail.variation_percent
                    ),
                )
            )

            for (
                column_index,
                value,
            ) in enumerate(values):
                item = QTableWidgetItem(
                    str(value)
                )

                if (
                    column_index
                    >= len(
                        context_columns
                    ) + 3
                ):
                    self._color_variation_item(
                        item,
                        detail.difference,
                    )

                self.detail_table.setItem(
                    row_index,
                    column_index,
                    item,
                )

        header = (
            self.detail_table
            .horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView
            .ResizeMode
            .ResizeToContents
        )

        header.setStretchLastSection(
            True
        )

        self.detail_search.textChanged.connect(
            self._filter_details
        )

        layout.addWidget(
            self.detail_table,
            1,
        )

        footer = QLabel(
            f"{len(all_details):,} "
            "cambios detectados"
        )

        footer.setObjectName(
            "summarySubtitle"
        )

        layout.addWidget(
            footer
        )

        return widget

    @staticmethod
    def _prepare_table(
        table,
    ):
        table.setEditTriggers(
            QAbstractItemView
            .EditTrigger
            .NoEditTriggers
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

        table.setAlternatingRowColors(
            True
        )

        table.setSortingEnabled(
            True
        )

        table.verticalHeader().setVisible(
            False
        )

    @staticmethod
    def _context_columns(
        details,
    ):
        result = []
        seen = set()

        for detail in details:
            for context in (
                detail.context
            ):
                if (
                    context.column
                    in seen
                ):
                    continue

                seen.add(
                    context.column
                )

                result.append(
                    (
                        context.column,
                        context.label,
                    )
                )

        return tuple(
            result
        )

    def _filter_details(
        self,
        text,
    ):
        needle = (
            text
            .strip()
            .lower()
        )

        for row_index in range(
            self.detail_table
            .rowCount()
        ):
            if not needle:
                self.detail_table.setRowHidden(
                    row_index,
                    False,
                )
                continue

            values = []

            for column_index in range(
                self.detail_table
                .columnCount()
            ):
                item = (
                    self.detail_table
                    .item(
                        row_index,
                        column_index,
                    )
                )

                if item is not None:
                    values.append(
                        item.text()
                        .lower()
                    )

            matches = any(
                needle in value
                for value in values
            )

            self.detail_table.setRowHidden(
                row_index,
                not matches,
            )

    @staticmethod
    def _field_label(
        column,
    ):
        if column == "habilitado":
            return "Estado"

        parts = [
            part
            for part in str(column)
            .strip()
            .split("_")
            if part
        ]

        if not parts:
            return ""

        if parts[0].lower() in (
            "anio",
            "ano",
            "annual",
        ):
            parts = [
                "total",
                "anual",
                *parts[1:],
            ]

        result = []

        for part in parts:
            if part.lower() == "usd":
                result.append(
                    "USD"
                )
            else:
                result.append(
                    part.capitalize()
                )

        return " ".join(
            result
        )

    @staticmethod
    def _format_value(
        value,
    ):
        if value is None:
            return ""

        if isinstance(
            value,
            bool,
        ):
            return (
                "Habilitado"
                if value
                else "Deshabilitado"
            )

        if isinstance(
            value,
            Decimal,
        ):
            return (
                f"US$ "
                f"{value:,.2f}"
            )

        return str(
            value
        )

    @staticmethod
    def _format_money(
        value,
    ):
        return (
            f"US$ {value:,.2f}"
        )

    @staticmethod
    def _format_difference(
        value,
    ):
        if value is None:
            return "-"

        if value > ZERO:
            return (
                f"+US$ "
                f"{value:,.2f}"
            )

        if value < ZERO:
            return (
                f"-US$ "
                f"{abs(value):,.2f}"
            )

        return "US$ 0.00"

    @staticmethod
    def _format_percent(
        value,
    ):
        if value is None:
            return "-"

        if value > ZERO:
            return (
                f"+{value:,.2f}%"
            )

        return (
            f"{value:,.2f}%"
        )

    @staticmethod
    def _variation_style(
        value,
    ):
        if value > ZERO:
            color = "#B42318"

        elif value < ZERO:
            color = "#067647"

        else:
            color = "#475467"

        return (
            f"color: {color}; "
            "font-weight: 700;"
        )

    @staticmethod
    def _color_variation_item(
        item,
        value,
    ):
        if value is None:
            return

        if value > ZERO:
            color = QColor(
                "#B42318"
            )

        elif value < ZERO:
            color = QColor(
                "#067647"
            )

        else:
            color = QColor(
                "#475467"
            )

        item.setForeground(
            QBrush(
                color
            )
        )
