from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


ZERO = Decimal("0.00")


class ApplyChangesDialog(QDialog):
    CONFIRMATION_TEXT = "CONFIRMAR"

    def __init__(
        self,
        summary,
        actor: str,
        parent=None,
    ):
        super().__init__(parent)

        self._summary = summary
        self._actor = actor

        self.setObjectName(
            "applyChangesDialog"
        )

        self.setWindowTitle(
            "Aplicar cambios OPEX"
        )

        self.setMinimumWidth(
            580
        )

        self._apply_style()
        self._setup_ui()

    def _apply_style(self):
        self.setStyleSheet(
            """
            QDialog#applyChangesDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QDialog#applyChangesDialog QLabel {
                color: #1F2937;
                background-color: transparent;
            }

            QFrame#summaryBox {
                background-color: #F2F4F7;
                border: 1px solid #D0D5DD;
                border-radius: 8px;
            }

            QLabel#warningText {
                background-color: #FFF4E5;
                color: #92400E;
                border: 1px solid #F3D3A3;
                border-radius: 7px;
                padding: 10px;
                font-weight: 600;
            }

            QLabel#persistenceText {
                background-color: #ECFDF3;
                color: #067647;
                border: 1px solid #ABEFC6;
                border-radius: 7px;
                padding: 10px;
                font-weight: 600;
            }

            QLineEdit {
                background-color: #F2F4F7;
                color: #111827;
                border: 1px solid #98A2B3;
                border-radius: 6px;
                padding: 9px 10px;
                font-weight: 600;
            }

            QLineEdit:focus {
                border: 2px solid #2F7650;
            }

            QDialogButtonBox QPushButton {
                background-color: #F2F4F7;
                color: #1F2937;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 8px 15px;
                min-width: 120px;
            }

            QPushButton#confirmApplyButton {
                background-color: #2F7650;
                color: #FFFFFF;
                border: 1px solid #2F7650;
                font-weight: 700;
            }

            QPushButton#confirmApplyButton:hover {
                background-color: #285F42;
            }

            QPushButton#confirmApplyButton:disabled {
                background-color: #D0D5DD;
                color: #667085;
                border-color: #D0D5DD;
            }
            """
        )

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            26,
            24,
            26,
            24,
        )

        layout.setSpacing(15)

        title = QLabel(
            "Aplicar cambios OPEX"
        )

        title.setStyleSheet(
            "font-size: 20px; "
            "font-weight: 700;"
        )

        layout.addWidget(
            title
        )

        warning = QLabel(
            "Esta operacion guardara de forma "
            "definitiva los cambios pendientes "
            "en BigQuery."
        )

        warning.setWordWrap(
            True
        )

        warning.setObjectName(
            "warningText"
        )

        layout.addWidget(
            warning
        )

        summary_box = QFrame()

        summary_box.setObjectName(
            "summaryBox"
        )

        summary_layout = QVBoxLayout(
            summary_box
        )

        summary_layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        rows_label = QLabel(
            "Filas modificadas: "
            f"{self._summary.pending_rows:,}"
        )

        fields_label = QLabel(
            "Campos modificados: "
            f"{self._summary.pending_fields:,}"
        )

        original_label = QLabel(
            "Presupuesto original: "
            f"US$ "
            f"{self._summary.original_total:,.2f}"
        )

        simulated_label = QLabel(
            "Presupuesto modificado: "
            f"US$ "
            f"{self._summary.simulated_total:,.2f}"
        )

        variation_label = QLabel(
            "Variacion total: "
            + self._format_difference(
                self._summary.difference
            )
        )

        variation_label.setStyleSheet(
            self._variation_style(
                self._summary.difference
            )
        )

        actor_label = QLabel(
            "Usuario: "
            + self._actor
        )

        actor_label.setStyleSheet(
            "color: #475467;"
        )

        summary_layout.addWidget(
            rows_label
        )

        summary_layout.addWidget(
            fields_label
        )

        summary_layout.addSpacing(
            5
        )

        summary_layout.addWidget(
            original_label
        )

        summary_layout.addWidget(
            simulated_label
        )

        summary_layout.addWidget(
            variation_label
        )

        summary_layout.addSpacing(
            5
        )

        summary_layout.addWidget(
            actor_label
        )

        layout.addWidget(
            summary_box
        )

        persistence = QLabel(
            "Los cambios se validaran antes de "
            "guardarse. Si otra sesion modifico "
            "una fila desde que cargaste el "
            "presupuesto, se detectara un "
            "conflicto y tus cambios locales "
            "se conservaran."
        )

        persistence.setWordWrap(
            True
        )

        persistence.setObjectName(
            "persistenceText"
        )

        layout.addWidget(
            persistence
        )

        instruction = QLabel(
            "Para continuar, escribe "
            "<b>CONFIRMAR</b> en el "
            "siguiente campo:"
        )

        layout.addWidget(
            instruction
        )

        self.confirmation_input = (
            QLineEdit()
        )

        self.confirmation_input.setPlaceholderText(
            "Escribe CONFIRMAR"
        )

        layout.addWidget(
            self.confirmation_input
        )

        self.buttons = (
            QDialogButtonBox(
                QDialogButtonBox
                .StandardButton.Ok
                |
                QDialogButtonBox
                .StandardButton.Cancel
            )
        )

        self.confirm_button = (
            self.buttons.button(
                QDialogButtonBox
                .StandardButton.Ok
            )
        )

        self.confirm_button.setText(
            "Aplicar cambios"
        )

        self.confirm_button.setObjectName(
            "confirmApplyButton"
        )

        self.confirm_button.setEnabled(
            False
        )

        cancel_button = (
            self.buttons.button(
                QDialogButtonBox
                .StandardButton.Cancel
            )
        )

        cancel_button.setText(
            "Cancelar"
        )

        self.buttons.accepted.connect(
            self.accept
        )

        self.buttons.rejected.connect(
            self.reject
        )

        self.confirmation_input.textChanged.connect(
            self._validate_confirmation
        )

        layout.addWidget(
            self.buttons
        )

    def _validate_confirmation(
        self,
        text,
    ):
        valid = (
            text.strip().upper()
            == self.CONFIRMATION_TEXT
        )

        self.confirm_button.setEnabled(
            valid
        )

    @staticmethod
    def _format_difference(
        value,
    ):
        if value > ZERO:
            return (
                f"+US$ {value:,.2f}"
            )

        if value < ZERO:
            return (
                f"-US$ {abs(value):,.2f}"
            )

        return "US$ 0.00"

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
