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

from app.config.capex_schema import (
    CAPEX_ML_MONTH_COLUMNS,
    CAPEX_USD_MONTH_COLUMNS,
)
from app.services.capex_cleaner import (
    CapexCleaningError,
    clean_capex_amount,
)


ZERO = Decimal(
    "0.000000000"
)


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


def capex_month_label(
    column,
):
    month = (
        str(column)
        .replace("_ml", "")
        .replace("_usd", "")
    )

    return MONTH_LABELS.get(
        month,
        month.replace(
            "_",
            " ",
        ).title(),
    )


class CapexAmountsDialog(
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
            "capexAmountsDialog"
        )

        self.setWindowTitle(
            "Importes de nueva inversion CAPEX"
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
            QDialog#capexAmountsDialog {
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
            "Importes CAPEX"
        )

        title.setObjectName(
            "amountTitle"
        )

        subtitle = QLabel(
            "Ingresa los importes mensuales "
            "en Moneda Local (ML) y USD.\n"
            "Los totales se calculan "
            "automaticamente desde los 12 meses. "
            "BigQuery todavia no sera modificado."
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

        tabs.addTab(
            self._build_family_tab(
                "ML",
                CAPEX_ML_MONTH_COLUMNS,
            ),
            "Moneda Local (ML)",
        )

        tabs.addTab(
            self._build_family_tab(
                "USD",
                CAPEX_USD_MONTH_COLUMNS,
            ),
            "USD",
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
        family,
        columns,
    ):
        widget = QWidget()

        layout = QVBoxLayout(
            widget
        )

        form = QFormLayout()

        form.setSpacing(
            9
        )

        for column in columns:
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
                capex_month_label(
                    column
                ),
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
                f"TOTAL {family}"
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
            family
        ] = total_value

        total_layout.addWidget(
            total_value
        )

        layout.addWidget(
            total_card
        )

        layout.addStretch()

        return widget

    def _family_values(
        self,
        columns,
    ):
        values = {}

        for column in columns:
            values[
                column
            ] = clean_capex_amount(
                self._inputs[
                    column
                ].text()
            )

        return values

    @staticmethod
    def _total(
        values,
    ):
        return sum(
            values.values(),
            ZERO,
        )

    def _refresh(
        self,
        *_,
    ):
        try:
            ml = self._family_values(
                CAPEX_ML_MONTH_COLUMNS
            )

            usd = self._family_values(
                CAPEX_USD_MONTH_COLUMNS
            )

        except CapexCleaningError as exc:
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

        ml_total = self._total(
            ml
        )

        usd_total = self._total(
            usd
        )

        self._total_labels[
            "ML"
        ].setText(
            f"{ml_total:,.2f}"
        )

        self._total_labels[
            "USD"
        ].setText(
            f"{usd_total:,.2f}"
        )

        self.status_label.setObjectName(
            "statusValid"
        )

        self.status_label.setText(
            "Importes validos. "
            "Los totales ML y USD se "
            "calcularan desde los meses."
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
            self.ml_values()
            self.usd_values()

        except CapexCleaningError as exc:
            self.status_label.setText(
                str(exc)
            )

            return

        self.accept()

    def ml_values(
        self,
    ):
        return self._family_values(
            CAPEX_ML_MONTH_COLUMNS
        )

    def usd_values(
        self,
    ):
        return self._family_values(
            CAPEX_USD_MONTH_COLUMNS
        )
