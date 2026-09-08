from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class GroupEditDialog(QDialog):
    def __init__(
        self,
        preview,
        parent=None,
        *,
        annual_column: str | None = None,
    ):
        super().__init__(parent)

        self._preview = preview
        self._annual_column = annual_column

        self.setObjectName(
            "groupEditDialog"
        )

        self.setWindowTitle(
            "Modificar agrupacion"
        )

        self.setMinimumWidth(
            560
        )

        self._apply_style()
        self._setup_ui()

        self.target_input.selectAll()
        self.target_input.setFocus()

    def _apply_style(self):
        self.setStyleSheet(
            """
            QDialog#groupEditDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QDialog#groupEditDialog QLabel {
                color: #1F2937;
                background-color: transparent;
            }

            QLabel#groupSummaryBox {
                background-color: #F1F3F5;
                border: 1px solid #D8DEE4;
                border-radius: 7px;
                padding: 10px 12px;
                color: #344054;
                font-weight: 600;
            }

            QLabel#valueBox {
                background-color: #F1F3F5;
                border: 1px solid #D8DEE4;
                border-radius: 6px;
                padding: 7px 9px;
                color: #1F2937;
            }

            QLineEdit#targetInput {
                background-color: #EDEFF2;
                color: #111827;
                border: 1px solid #BFC7D0;
                border-radius: 6px;
                padding: 8px 10px;
                font-weight: 600;
            }

            QLineEdit#targetInput:focus {
                border: 2px solid #4E8F67;
            }

            QLabel#informationBox {
                background-color: #F8F9FA;
                border: 1px solid #E1E5EA;
                border-radius: 6px;
                padding: 9px;
                color: #475467;
            }

            QDialogButtonBox QPushButton {
                background-color: #F3F4F6;
                color: #1F2937;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 7px 14px;
                min-width: 100px;
            }

            QDialogButtonBox QPushButton:hover {
                background-color: #E7EAED;
            }

            QPushButton#primaryButton {
                background-color: #2F7650;
                color: #FFFFFF;
                border: 1px solid #2F7650;
                font-weight: 600;
            }

            QPushButton#primaryButton:hover {
                background-color: #285F42;
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

        layout.setSpacing(14)

        title = QLabel(
            "Modificar presupuesto agrupado"
        )

        title.setStyleSheet(
            "font-size: 19px; font-weight: 700;"
        )

        layout.addWidget(title)

        group_text = " / ".join(
            f"{column.replace('_', ' ').title()}: {value}"
            for column, value
            in zip(
                self._preview.group_columns,
                self._preview.group_values,
            )
        )

        group_label = QLabel(
            group_text
        )

        group_label.setWordWrap(
            True
        )

        group_label.setObjectName(
            "groupSummaryBox"
        )

        layout.addWidget(
            group_label
        )

        form = QFormLayout()

        form.setSpacing(10)

        self.column_value = QLabel(
            self._preview.column
            .replace("_", " ")
            .upper()
        )

        self.column_value.setObjectName(
            "valueBox"
        )

        self.rows_value = QLabel(
            f"{self._preview.row_count:,}"
        )

        self.rows_value.setObjectName(
            "valueBox"
        )

        self.current_value = QLabel(
            self._format_money(
                self._preview.current_total
            )
        )

        self.current_value.setObjectName(
            "valueBox"
        )

        self.target_input = QLineEdit(
            f"{self._preview.current_total:.2f}"
        )

        self.target_input.setObjectName(
            "targetInput"
        )

        self.target_input.setPlaceholderText(
            "Nuevo total USD"
        )

        self.difference_value = QLabel(
            "US$ 0.00"
        )

        self.difference_value.setObjectName(
            "valueBox"
        )

        self.variation_value = QLabel(
            "0.00 %"
        )

        self.variation_value.setObjectName(
            "valueBox"
        )

        form.addRow(
            "Campo:",
            self.column_value,
        )

        form.addRow(
            "Filas afectadas:",
            self.rows_value,
        )

        form.addRow(
            "Total actual:",
            self.current_value,
        )

        form.addRow(
            "Nuevo total:",
            self.target_input,
        )

        form.addRow(
            "Diferencia:",
            self.difference_value,
        )

        form.addRow(
            "Variacion:",
            self.variation_value,
        )

        layout.addLayout(
            form
        )

        if (
            self._annual_column is not None
            and
            self._preview.column
            == self._annual_column
        ):
            explanation = (
                "El nuevo total anual se distribuira "
                "proporcionalmente usando la "
                "distribucion mensual actual de "
                "todos los registros habilitados "
                "del grupo."
            )
        else:
            explanation = (
                "Solo se redistribuira este mes "
                "entre los registros habilitados "
                "del grupo. Los demas meses no "
                "seran modificados."
            )

        note = QLabel(
            explanation
        )

        note.setWordWrap(
            True
        )

        note.setObjectName(
            "informationBox"
        )

        layout.addWidget(
            note
        )

        self.validation_label = QLabel(
            ""
        )

        self.validation_label.setWordWrap(
            True
        )

        self.validation_label.setObjectName(
            "informationBox"
        )

        layout.addWidget(
            self.validation_label
        )

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            |
            QDialogButtonBox.StandardButton.Cancel
        )

        apply_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )

        apply_button.setText(
            "Aplicar simulacion"
        )

        apply_button.setObjectName(
            "primaryButton"
        )

        cancel_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Cancel
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

        layout.addWidget(
            self.buttons
        )

        self.target_input.textChanged.connect(
            self._update_preview
        )

        self._update_preview()

    def target_total(
        self,
    ) -> Decimal:
        text = (
            self.target_input
            .text()
            .strip()
            .replace("US$", "")
            .replace("$", "")
            .replace(" ", "")
            .replace(",", "")
        )

        if not text:
            raise ValueError(
                "Debe ingresar un nuevo total."
            )

        try:
            value = Decimal(text)

        except InvalidOperation as exc:
            raise ValueError(
                "El importe ingresado no es valido."
            ) from exc

        if value < ZERO:
            raise ValueError(
                "El presupuesto no puede ser negativo."
            )

        return value.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    def _update_preview(self):
        apply_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )

        try:
            target = self.target_total()

        except ValueError as exc:
            self.validation_label.setText(
                str(exc)
            )

            self.difference_value.setText(
                "-"
            )

            self.variation_value.setText(
                "-"
            )

            apply_button.setEnabled(
                False
            )

            return

        difference = (
            target
            - self._preview.current_total
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if self._preview.current_total == ZERO:
            variation = None
        else:
            variation = (
                difference
                / self._preview.current_total
                * Decimal("100")
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

        self.difference_value.setText(
            self._format_signed_money(
                difference
            )
        )

        if variation is None:
            self.variation_value.setText(
                "No aplica"
            )
        else:
            sign = (
                "+"
                if variation > ZERO
                else ""
            )

            self.variation_value.setText(
                f"{sign}{variation:,.2f} %"
            )

        self._set_variation_style(
            difference
        )

        self.validation_label.setText(
            "La operacion permanecera "
            "solo en el Workspace local."
        )

        apply_button.setEnabled(
            True
        )

    def _set_variation_style(
        self,
        difference,
    ):
        if difference > ZERO:
            color = "#B42318"
        elif difference < ZERO:
            color = "#067647"
        else:
            color = "#475467"

        style = (
            "background-color: #F1F3F5;"
            "border: 1px solid #D8DEE4;"
            "border-radius: 6px;"
            "padding: 7px 9px;"
            f"color: {color};"
            "font-weight: 700;"
        )

        self.difference_value.setStyleSheet(
            style
        )

        self.variation_value.setStyleSheet(
            style
        )

    @staticmethod
    def _format_money(
        value: Decimal,
    ) -> str:
        return f"US$ {value:,.2f}"

    @staticmethod
    def _format_signed_money(
        value: Decimal,
    ) -> str:
        if value > ZERO:
            return f"+US$ {value:,.2f}"

        if value < ZERO:
            return f"-US$ {abs(value):,.2f}"

        return "US$ 0.00"