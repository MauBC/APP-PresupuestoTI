from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config.presupuesto_schema import (
    AMOUNT_GROUPS,
    MONTHS,
)
from app.services.opex_new_row_amount_service import (
    OpexNewRowAmountError,
    clean_opex_new_row_amount,
)


ZERO = Decimal("0.00")


MONTH_LABELS = {
    "enero": "Enero",
    "febrero": "Febrero",
    "marzo": "Marzo",
    "abril": "Abril",
    "mayo": "Mayo",
    "junio": "Junio",
    "julio": "Julio",
    "agosto": "Agosto",
    "setiembre": "Setiembre",
    "octubre": "Octubre",
    "noviembre": "Noviembre",
    "diciembre": "Diciembre",
}


FAMILY_LABELS = {
    "mf":
        "Moneda de facturacion (MF)",
    "usd":
        "USD",
    "ml":
        "Moneda local (ML)",
}


class OpexAmountsDialog(
    QDialog
):
    def __init__(
        self,
        *,
        row,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._row = dict(
            row
        )

        self._inputs = {}
        self._total_labels = {}

        self.setObjectName(
            "opexAmountsDialog"
        )

        self.setWindowTitle(
            "Importes de nueva fila OPEX"
        )

        self.resize(
            720,
            720,
        )

        self.setMinimumSize(
            620,
            600,
        )

        self._apply_style()
        self._setup_ui()
        self._refresh()

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#opexAmountsDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QLabel {
                color: #1F2937;
            }

            QLabel#amountTitle {
                font-size: 20px;
                font-weight: 700;
            }

            QLabel#amountSubtitle {
                color: #667085;
                font-size: 12px;
            }

            QFrame#totalCard {
                background-color: #F3F4F6;
                border: 1px solid #D8DEE4;
                border-radius: 8px;
            }

            QLabel#totalValue {
                color: #2F7650;
                font-size: 18px;
                font-weight: 700;
            }

            QLineEdit {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #98A2B3;
                border-radius: 6px;
                padding: 7px;
                min-width: 180px;
            }

            QLineEdit:focus {
                border: 2px solid #2F7650;
            }

            QTabWidget::pane {
                border: 1px solid #D8DEE4;
                background-color: #FFFFFF;
            }

            QTabBar::tab {
                background-color: #EEF1F4;
                color: #344054;
                padding: 9px 16px;
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

            QPushButton#applyButton {
                background-color: #2F7650;
                color: #FFFFFF;
                border-color: #2F7650;
                font-weight: 700;
            }

            QPushButton#applyButton:disabled {
                background-color: #D0D5DD;
                color: #667085;
                border-color: #D0D5DD;
            }

            QLabel#statusInvalid {
                color: #B42318;
                background-color: #FEF3F2;
                border: 1px solid #FECDCA;
                border-radius: 6px;
                padding: 8px;
            }

            QLabel#statusValid {
                color: #067647;
                background-color: #ECFDF3;
                border: 1px solid #ABEFC6;
                border-radius: 6px;
                padding: 8px;
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
            12
        )

        title = QLabel(
            "Importes OPEX"
        )

        title.setObjectName(
            "amountTitle"
        )

        subtitle = QLabel(
            "Ingresa los importes mensuales "
            "de MF, USD y ML. "
            "Los tres totales anuales se "
            "calculan automaticamente desde "
            "los 12 meses. BigQuery no cambia "
            "hasta usar Aplicar cambios."
        )

        subtitle.setObjectName(
            "amountSubtitle"
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

        tabs = QTabWidget()

        for group in AMOUNT_GROUPS:
            tabs.addTab(
                self._build_family_tab(
                    group
                ),
                FAMILY_LABELS[group],
            )

        layout.addWidget(
            tabs,
            1,
        )

        self.status_label = QLabel()

        self.status_label.setWordWrap(
            True
        )

        layout.addWidget(
            self.status_label
        )

        actions = QHBoxLayout()

        actions.addStretch()

        cancel_button = QPushButton(
            "Cancelar"
        )

        cancel_button.clicked.connect(
            self.reject
        )

        self.apply_button = QPushButton(
            "Agregar al Workspace"
        )

        self.apply_button.setObjectName(
            "applyButton"
        )

        self.apply_button.clicked.connect(
            self._accept_values
        )

        actions.addWidget(
            cancel_button
        )

        actions.addWidget(
            self.apply_button
        )

        layout.addLayout(
            actions
        )

    def _build_family_tab(
        self,
        group,
    ):
        widget = QWidget()

        layout = QVBoxLayout(
            widget
        )

        form = QFormLayout()

        form.setSpacing(
            9
        )

        for month in MONTHS:
            column = (
                f"{month}_{group}"
            )

            input_widget = QLineEdit()

            value = self._row.get(
                column,
                ZERO,
            )

            input_widget.setText(
                str(
                    value
                    if value is not None
                    else ZERO
                )
            )

            input_widget.setPlaceholderText(
                "0.00"
            )

            input_widget.textChanged.connect(
                self._refresh
            )

            self._inputs[
                column
            ] = input_widget

            form.addRow(
                MONTH_LABELS[
                    month
                ],
                input_widget,
            )

        layout.addLayout(
            form
        )

        total_card = QFrame()

        total_card.setObjectName(
            "totalCard"
        )

        total_layout = QHBoxLayout(
            total_card
        )

        total_layout.addWidget(
            QLabel(
                "TOTAL "
                + group.upper()
            )
        )

        total_layout.addStretch()

        total_value = QLabel(
            "0.00"
        )

        total_value.setObjectName(
            "totalValue"
        )

        self._total_labels[
            group
        ] = total_value

        total_layout.addWidget(
            total_value
        )

        layout.addWidget(
            total_card
        )

        layout.addStretch()

        return widget

    def monthly_values(
        self,
    ):
        result = {}

        for group in AMOUNT_GROUPS:
            for month in MONTHS:
                column = (
                    f"{month}_{group}"
                )

                result[column] = (
                    clean_opex_new_row_amount(
                        self._inputs[
                            column
                        ].text()
                    )
                )

        return result

    def _refresh(
        self,
        *_,
    ):
        try:
            values = (
                self.monthly_values()
            )

        except OpexNewRowAmountError as exc:
            self.status_label.setObjectName(
                "statusInvalid"
            )

            self.status_label.setText(
                str(exc)
            )

            self.apply_button.setEnabled(
                False
            )

            self._refresh_style(
                self.status_label
            )

            return

        for group in AMOUNT_GROUPS:
            total = sum(
                (
                    values[
                        f"{month}_{group}"
                    ]
                    for month in MONTHS
                ),
                ZERO,
            )

            self._total_labels[
                group
            ].setText(
                f"{total:,.2f}"
            )

        self.status_label.setObjectName(
            "statusValid"
        )

        self.status_label.setText(
            "Importes validos. "
            "TOTAL MF, TOTAL USD y TOTAL ML "
            "se calcularan automaticamente."
        )

        self.apply_button.setEnabled(
            True
        )

        self._refresh_style(
            self.status_label
        )

    @staticmethod
    def _refresh_style(
        widget,
    ):
        widget.style().unpolish(
            widget
        )

        widget.style().polish(
            widget
        )

        widget.update()

    def _accept_values(
        self,
    ):
        try:
            self.monthly_values()

        except OpexNewRowAmountError as exc:
            self.status_label.setText(
                str(exc)
            )

            return

        self.accept()
