from decimal import Decimal

from PySide6.QtGui import (
    QBrush,
    QColor,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


ZERO = Decimal("0.00")


class ChangeDetailsDialog(
    QDialog
):
    def __init__(
        self,
        summary,
        module_label: str,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._summary = summary
        self._module_label = (
            module_label
        )

        self.setWindowTitle(
            "Detalle de cambios "
            f"{module_label}"
        )

        self.resize(
            1180,
            620,
        )

        self._setup_ui()

    def _setup_ui(
        self,
    ):
        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            20,
            20,
            20,
            20,
        )

        layout.setSpacing(
            12
        )

        title = QLabel(
            "Detalle de cambios "
            f"{self._module_label}"
        )

        title.setStyleSheet(
            "font-size: 19px; "
            "font-weight: 700;"
        )

        layout.addWidget(
            title
        )

        description = QLabel(
            "Cada fila muestra un campo "
            "modificado y el registro "
            "presupuestal afectado."
        )

        description.setStyleSheet(
            "color: #475467;"
        )

        layout.addWidget(
            description
        )

        context_columns = (
            self._context_columns()
        )

        headers = [
            *(
                label
                for _, label
                in context_columns
            ),
            "Campo",
            "Antes",
            "Despues",
            "Variacion",
        ]

        table = QTableWidget(
            len(
                self._summary.details
            ),
            len(
                headers
            ),
        )

        table.setHorizontalHeaderLabels(
            headers
        )

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

        table.setAlternatingRowColors(
            True
        )

        table.verticalHeader().setVisible(
            False
        )

        for row_index, detail in enumerate(
            self._summary.details
        ):
            context_map = (
                detail.context_map
            )

            column_index = 0

            for (
                context_column,
                _,
            ) in context_columns:
                table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(
                        context_map.get(
                            context_column,
                            "(Sin valor)",
                        )
                    ),
                )

                column_index += 1

            table.setItem(
                row_index,
                column_index,
                QTableWidgetItem(
                    self._field_label(
                        detail.column
                    )
                ),
            )

            column_index += 1

            table.setItem(
                row_index,
                column_index,
                QTableWidgetItem(
                    self._format_value(
                        detail.before
                    )
                ),
            )

            column_index += 1

            table.setItem(
                row_index,
                column_index,
                QTableWidgetItem(
                    self._format_value(
                        detail.after
                    )
                ),
            )

            column_index += 1

            variation_item = (
                QTableWidgetItem(
                    self._format_difference(
                        detail.difference
                    )
                )
            )

            self._style_variation_item(
                variation_item,
                detail.difference,
            )

            table.setItem(
                row_index,
                column_index,
                variation_item,
            )

        header = (
            table.horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView
            .ResizeMode
            .ResizeToContents
        )

        header.setStretchLastSection(
            True
        )

        layout.addWidget(
            table,
            1,
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox
            .StandardButton
            .Close
        )

        close_button = (
            buttons.button(
                QDialogButtonBox
                .StandardButton
                .Close
            )
        )

        close_button.setText(
            "Cerrar"
        )

        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(
            buttons
        )

    def _context_columns(
        self,
    ):
        result = []
        seen = set()

        for detail in (
            self._summary.details
        ):
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
                f"US$ {value:,.2f}"
            )

        return str(
            value
        )

    @staticmethod
    def _format_difference(
        value,
    ):
        if value is None:
            return "-"

        if value > ZERO:
            return (
                f"+US$ {value:,.2f}"
            )

        if value < ZERO:
            return (
                f"-US$ "
                f"{abs(value):,.2f}"
            )

        return "US$ 0.00"

    @staticmethod
    def _style_variation_item(
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


class ApplyChangesDialog(
    QDialog
):
    CONFIRMATION_TEXT = "CONFIRMAR"

    def __init__(
        self,
        summary,
        actor: str,
        parent=None,
        *,
        module_label: str = "OPEX",
    ):
        super().__init__(
            parent
        )

        self._summary = summary
        self._actor = actor
        self._module_label = (
            module_label
        )

        self.setObjectName(
            "applyChangesDialog"
        )

        self.setWindowTitle(
            "Aplicar cambios "
            f"{module_label}"
        )

        self.setMinimumWidth(
            580
        )

        self._apply_style()
        self._setup_ui()

    def _apply_style(
        self,
    ):
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

            QDialogButtonBox QPushButton,
            QPushButton#detailButton {
                background-color: #F2F4F7;
                color: #1F2937;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 8px 15px;
                min-width: 120px;
            }

            QPushButton#detailButton:hover {
                border-color: #2F7650;
                color: #2F7650;
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

    def _setup_ui(
        self,
    ):
        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            26,
            24,
            26,
            24,
        )

        layout.setSpacing(
            15
        )

        title = QLabel(
            "Aplicar cambios "
            f"{self._module_label}"
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

        self.detail_button = QPushButton(
            "Ver detalle "
            f"({len(self._summary.details):,})"
        )

        self.detail_button.setObjectName(
            "detailButton"
        )

        self.detail_button.setEnabled(
            bool(
                self._summary.details
            )
        )

        self.detail_button.clicked.connect(
            self._show_details
        )

        layout.addWidget(
            self.detail_button
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

    def _show_details(
        self,
    ):
        dialog = ChangeDetailsDialog(
            self._summary,
            self._module_label,
            self,
        )

        dialog.exec()

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
