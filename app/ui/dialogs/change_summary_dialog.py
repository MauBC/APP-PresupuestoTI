from decimal import Decimal

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
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
    ):
        super().__init__(parent)

        self._summary = summary

        self.setObjectName(
            "changeSummaryDialog"
        )

        self.setWindowTitle(
            "Resumen de cambios"
        )

        self.resize(
            1150,
            720,
        )

        self._apply_style()
        self._setup_ui()

    def _apply_style(self):
        self.setStyleSheet(
            """
            QDialog#changeSummaryDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QDialog#changeSummaryDialog QLabel {
                color: #1F2937;
                background-color: transparent;
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
                font-size: 18px;
                font-weight: 700;
            }

            QTabWidget::pane {
                border: 1px solid #D8DEE4;
                background-color: #FFFFFF;
            }

            QTabBar::tab {
                background-color: #EEF1F4;
                color: #344054;
                padding: 8px 16px;
                border: 1px solid #D8DEE4;
            }

            QTabBar::tab:selected {
                background-color: #FFFFFF;
                font-weight: 600;
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
                padding: 6px;
                font-weight: 600;
            }

            QPushButton {
                background-color: #F3F4F6;
                color: #1F2937;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 7px 16px;
            }

            QPushButton:hover {
                background-color: #E8EBEE;
            }
            """
        )

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            24,
            22,
            24,
            22,
        )

        layout.setSpacing(16)

        title = QLabel(
            "Resumen de la simulacion"
        )

        title.setStyleSheet(
            "font-size: 20px; font-weight: 700;"
        )

        subtitle = QLabel(
            f"{self._summary.pending_rows:,} filas "
            f"modificadas | "
            f"{self._summary.pending_fields:,} "
            "campos modificados"
        )

        subtitle.setStyleSheet(
            "color: #667085;"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)

        cards = QHBoxLayout()

        cards.addWidget(
            self._create_card(
                "Presupuesto original",
                self._format_money(
                    self._summary.original_total
                ),
            )
        )

        cards.addWidget(
            self._create_card(
                "Presupuesto simulado",
                self._format_money(
                    self._summary.simulated_total
                ),
            )
        )

        cards.addWidget(
            self._create_card(
                "Variacion total",
                self._format_signed_money(
                    self._summary.difference
                ),
                self._difference_color(
                    self._summary.difference
                ),
            )
        )

        cards.addWidget(
            self._create_card(
                "Variacion %",
                self._format_percent(
                    self._summary.variation_percent
                ),
                self._difference_color(
                    self._summary.difference
                ),
            )
        )

        layout.addLayout(cards)

        tabs = QTabWidget()

        tabs.addTab(
            self._build_breakdown_table(
                self._summary.by_country,
                "Pais",
            ),
            "Por pais",
        )

        tabs.addTab(
            self._build_breakdown_table(
                self._summary.by_budgeter,
                "Presupuestador",
            ),
            "Por presupuestador",
        )

        tabs.addTab(
            self._build_detail_tab(),
            "Detalle",
        )

        layout.addWidget(
            tabs,
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

    def _create_card(
        self,
        title,
        value,
        value_color=None,
    ):
        frame = QFrame()

        frame.setObjectName(
            "summaryCard"
        )

        layout = QVBoxLayout(frame)

        layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "cardTitle"
        )

        value_label = QLabel(
            value
        )

        value_label.setObjectName(
            "cardValue"
        )

        if value_color:
            value_label.setStyleSheet(
                "font-size: 18px; "
                "font-weight: 700; "
                f"color: {value_color};"
            )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            value_label
        )

        return frame

    def _build_breakdown_table(
        self,
        rows,
        first_header,
    ):
        table = QTableWidget(
            len(rows),
            5,
        )

        table.setHorizontalHeaderLabels(
            [
                first_header,
                "Original",
                "Simulado",
                "Variacion",
                "Variacion %",
            ]
        )

        table.setAlternatingRowColors(
            True
        )

        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        table.verticalHeader().setVisible(
            False
        )

        for row_index, row in enumerate(
            rows
        ):
            values = [
                row.key,
                self._format_money(
                    row.original_total
                ),
                self._format_money(
                    row.simulated_total
                ),
                self._format_signed_money(
                    row.difference
                ),
                self._format_percent(
                    row.variation_percent
                ),
            ]

            for column_index, value in enumerate(
                values
            ):
                item = QTableWidgetItem(
                    str(value)
                )

                if column_index in (
                    3,
                    4,
                ):
                    item.setForeground(
                        QColor(
                            self._difference_color(
                                row.difference
                            )
                        )
                    )

                table.setItem(
                    row_index,
                    column_index,
                    item,
                )

        header = table.horizontalHeader()

        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        return table

    def _build_detail_tab(self):
        widget = QWidget()

        layout = QVBoxLayout(widget)

        details = self._summary.details[
            :self.MAX_DETAILS
        ]

        if (
            len(self._summary.details)
            > self.MAX_DETAILS
        ):
            warning = QLabel(
                "Se muestran los primeros "
                f"{self.MAX_DETAILS:,} cambios."
            )

            warning.setStyleSheet(
                "color: #667085;"
            )

            layout.addWidget(
                warning
            )

        table = QTableWidget(
            len(details),
            7,
        )

        table.setHorizontalHeaderLabels(
            [
                "Fila",
                "Pais",
                "Presupuestador",
                "Gasto",
                "Campo",
                "Antes",
                "Ahora",
            ]
        )

        table.setAlternatingRowColors(
            True
        )

        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        table.verticalHeader().setVisible(
            False
        )

        for row_index, detail in enumerate(
            details
        ):
            values = [
                detail.session_row_id + 1,
                detail.pais,
                detail.presupuestador,
                detail.nombre_gasto,
                detail.column
                .replace("_", " ")
                .upper(),
                self._format_value(
                    detail.before
                ),
                self._format_value(
                    detail.after
                ),
            ]

            for column_index, value in enumerate(
                values
            ):
                table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(
                        str(value)
                    ),
                )

        header = table.horizontalHeader()

        header.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        header.setStretchLastSection(
            True
        )

        layout.addWidget(
            table
        )

        return widget

    @staticmethod
    def _difference_color(
        difference,
    ):
        if difference > ZERO:
            return "#B42318"

        if difference < ZERO:
            return "#067647"

        return "#475467"

    @staticmethod
    def _format_money(
        value,
    ):
        return f"US$ {value:,.2f}"

    @staticmethod
    def _format_signed_money(
        value,
    ):
        if value > ZERO:
            return f"+US$ {value:,.2f}"

        if value < ZERO:
            return f"-US$ {abs(value):,.2f}"

        return "US$ 0.00"

    @staticmethod
    def _format_percent(
        value,
    ):
        if value is None:
            return "No aplica"

        sign = (
            "+"
            if value > ZERO
            else ""
        )

        return f"{sign}{value:,.2f} %"

    @staticmethod
    def _format_value(
        value,
    ):
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