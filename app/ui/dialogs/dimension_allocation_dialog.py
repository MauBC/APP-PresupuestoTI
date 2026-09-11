from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")


def build_equal_percentages(
    values,
):
    values = tuple(
        values
    )

    if not values:
        return {}

    base = (
        HUNDRED
        / Decimal(
            len(values)
        )
    ).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )

    result = {
        value: base
        for value in values
    }

    residual = (
        HUNDRED
        - sum(
            result.values(),
            ZERO,
        )
    ).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )

    result[
        values[-1]
    ] += residual

    return result


class DimensionAllocationDialog(
    QDialog
):
    def __init__(
        self,
        *,
        service,
        dimension: str,
        dimension_label: str,
        scope_columns=(),
        scope_values=(),
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._service = service
        self._dimension = dimension
        self._dimension_label = (
            dimension_label
        )

        self._scope_columns = tuple(
            scope_columns
        )

        self._scope_values = tuple(
            scope_values
        )

        self._initial_preview = (
            service.current_preview(
                dimension=dimension,
                scope_columns=(
                    self._scope_columns
                ),
                scope_values=(
                    self._scope_values
                ),
            )
        )

        self._initial_percentages = {
            item.value:
                item.percentage
            for item
            in self._initial_preview.items
        }

        self._percentage_inputs = {}
        self._target_items = {}
        self._difference_items = {}
        self._variation_items = {}

        self.setObjectName(
            "dimensionAllocationDialog"
        )

        self.setWindowTitle(
            "Distribuir por "
            + dimension_label
        )

        self.resize(
            1000,
            700,
        )

        self.setMinimumSize(
            850,
            580,
        )

        self._apply_style()
        self._setup_ui()

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#dimensionAllocationDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QLabel {
                color: #1F2937;
            }

            QLineEdit {
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #98A2B3;
                border-radius: 4px;
                padding: 2px 4px;
            }

            QLineEdit:focus {
                border: 2px solid #2F7650;
            }

            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F8F9FA;
                gridline-color: #E5E7EB;
                color: #1F2937;
            }

            QHeaderView::section {
                background-color: #EEF1F4;
                color: #344054;
                padding: 7px;
                border: 0;
                border-right: 1px solid #D8DEE4;
                border-bottom: 1px solid #D8DEE4;
                font-weight: 600;
            }

            QPushButton {
                background-color: #F2F4F7;
                color: #1F2937;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 8px 14px;
            }

            QPushButton:hover {
                border-color: #2F7650;
                color: #2F7650;
            }

            QPushButton#applyAllocationButton {
                background-color: #2F7650;
                color: #FFFFFF;
                border-color: #2F7650;
                font-weight: 700;
            }

            QPushButton#applyAllocationButton:disabled {
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
            12
        )

        title = QLabel(
            "Distribuir presupuesto por "
            + self._dimension_label
        )

        title.setStyleSheet(
            "font-size: 20px; "
            "font-weight: 700;"
        )

        layout.addWidget(
            title
        )

        subtitle = QLabel(
            "Redistribuye el presupuesto "
            "anual conservando la proporcion "
            "mensual interna de cada grupo."
        )

        subtitle.setWordWrap(
            True
        )

        subtitle.setStyleSheet(
            "color: #667085;"
        )

        layout.addWidget(
            subtitle
        )

        total_label = QLabel(
            "Presupuesto del alcance: "
            f"US$ "
            f"{self._initial_preview.current_total:,.2f}"
        )

        total_label.setStyleSheet(
            "font-size: 15px; "
            "font-weight: 700;"
        )

        layout.addWidget(
            total_label
        )

        scope = QLabel(
            self._scope_text()
        )

        scope.setWordWrap(
            True
        )

        scope.setStyleSheet(
            "background-color: #F2F4F7; "
            "border: 1px solid #D0D5DD; "
            "border-radius: 6px; "
            "padding: 8px; "
            "color: #475467;"
        )

        layout.addWidget(
            scope
        )

        search_layout = QHBoxLayout()

        search_layout.addWidget(
            QLabel("Buscar:")
        )

        self.search_input = (
            QLineEdit()
        )

        self.search_input.setPlaceholderText(
            "Buscar "
            + self._dimension_label
            + "..."
        )

        search_layout.addWidget(
            self.search_input,
            1,
        )

        layout.addLayout(
            search_layout
        )

        self.table = QTableWidget(
            len(
                self._initial_preview.items
            ),
            7,
        )

        self.table.setHorizontalHeaderLabels(
            [
                self._dimension_label.upper(),
                "FILAS",
                "ACTUAL",
                "% NUEVO",
                "NUEVO IMPORTE",
                "DIFERENCIA",
                "VARIACION %",
            ]
        )

        self.table.setEditTriggers(
            QAbstractItemView
            .EditTrigger
            .NoEditTriggers
        )

        self.table.setSelectionMode(
            QAbstractItemView
            .SelectionMode
            .NoSelection
        )

        self.table.setAlternatingRowColors(
            True
        )

        self.table.verticalHeader().setVisible(
            False
        )

        self.table.verticalHeader().setDefaultSectionSize(
            34
        )

        for (
            row_index,
            item,
        ) in enumerate(
            self._initial_preview.items
        ):
            self.table.setItem(
                row_index,
                0,
                QTableWidgetItem(
                    str(
                        item.value
                    )
                ),
            )

            self.table.setItem(
                row_index,
                1,
                QTableWidgetItem(
                    f"{item.row_count:,}"
                ),
            )

            self.table.setItem(
                row_index,
                2,
                QTableWidgetItem(
                    self._money(
                        item.current_total
                    )
                ),
            )

            percentage_input = (
                QLineEdit()
            )

            percentage_input.setText(
                f"{item.percentage:.2f}"
            )

            percentage_input.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            percentage_input.setFixedHeight(
                26
            )

            percentage_input.setMinimumWidth(
                72
            )

            percentage_input.setMaximumWidth(
                86
            )

            self._percentage_inputs[
                item.value
            ] = percentage_input

            self.table.setCellWidget(
                row_index,
                3,
                percentage_input,
            )

            target_item = (
                QTableWidgetItem()
            )

            difference_item = (
                QTableWidgetItem()
            )

            variation_item = (
                QTableWidgetItem()
            )

            self._target_items[
                item.value
            ] = target_item

            self._difference_items[
                item.value
            ] = difference_item

            self._variation_items[
                item.value
            ] = variation_item

            self.table.setItem(
                row_index,
                4,
                target_item,
            )

            self.table.setItem(
                row_index,
                5,
                difference_item,
            )

            self.table.setItem(
                row_index,
                6,
                variation_item,
            )

            percentage_input.textChanged.connect(
                self._refresh_preview
            )

        header = (
            self.table
            .horizontalHeader()
        )

        header.setSectionResizeMode(
            0,
            QHeaderView
            .ResizeMode
            .Stretch,
        )

        for index in (
            1,
            2,
            4,
            5,
            6,
        ):
            header.setSectionResizeMode(
                index,
                QHeaderView
                .ResizeMode
                .ResizeToContents,
            )

        header.setSectionResizeMode(
            3,
            QHeaderView
            .ResizeMode
            .Fixed,
        )

        self.table.setColumnWidth(
            3,
            96,
        )

        layout.addWidget(
            self.table,
            1,
        )

        self.status_label = QLabel()

        self.status_label.setWordWrap(
            True
        )

        layout.addWidget(
            self.status_label
        )

        tools = QHBoxLayout()

        self.equal_button = QPushButton(
            "Distribucion uniforme"
        )

        self.restore_button = QPushButton(
            "Restaurar actual"
        )

        tools.addWidget(
            self.equal_button
        )

        tools.addWidget(
            self.restore_button
        )

        tools.addStretch()

        layout.addLayout(
            tools
        )

        buttons = QHBoxLayout()

        buttons.addStretch()

        cancel_button = QPushButton(
            "Cancelar"
        )

        self.apply_button = QPushButton(
            "Aplicar distribucion"
        )

        self.apply_button.setObjectName(
            "applyAllocationButton"
        )

        self.apply_button.setEnabled(
            False
        )

        buttons.addWidget(
            cancel_button
        )

        buttons.addWidget(
            self.apply_button
        )

        layout.addLayout(
            buttons
        )

        self.search_input.textChanged.connect(
            self._filter_rows
        )

        self.equal_button.clicked.connect(
            self._set_equal
        )

        self.restore_button.clicked.connect(
            self._restore
        )

        cancel_button.clicked.connect(
            self.reject
        )

        self.apply_button.clicked.connect(
            self._accept
        )

        self._refresh_preview()

    def percentages(
        self,
    ):
        return self._read_percentages()

    def _read_percentages(
        self,
    ):
        result = {}

        for value, widget in (
            self._percentage_inputs
            .items()
        ):
            text = (
                widget.text()
                .strip()
                .replace("%", "")
                .replace(",", ".")
            )

            if not text:
                raise ValueError(
                    "Todos los porcentajes "
                    "deben tener un valor."
                )

            try:
                percentage = Decimal(
                    text
                )

            except InvalidOperation as exc:
                raise ValueError(
                    "Existe un porcentaje "
                    "no valido."
                ) from exc

            percentage = (
                percentage.quantize(
                    CENT,
                    rounding=ROUND_HALF_UP,
                )
            )

            if percentage < ZERO:
                raise ValueError(
                    "Los porcentajes no "
                    "pueden ser negativos."
                )

            result[value] = (
                percentage
            )

        return result

    def _refresh_preview(
        self,
        *_,
    ):
        try:
            percentages = (
                self._read_percentages()
            )

        except ValueError as exc:
            self._set_invalid(
                str(exc)
            )
            return

        total = sum(
            percentages.values(),
            ZERO,
        )

        if total != HUNDRED:
            self._show_approximate(
                percentages
            )

            if total < HUNDRED:
                self._set_warning(
                    "Distribuido: "
                    f"{total:.2f}% | "
                    f"Falta "
                    f"{HUNDRED - total:.2f}%."
                )

            else:
                self._set_invalid(
                    "Distribuido: "
                    f"{total:.2f}% | "
                    f"Exceso "
                    f"{total - HUNDRED:.2f}%."
                )

            return

        try:
            preview = (
                self._service
                .preview(
                    dimension=(
                        self._dimension
                    ),
                    percentages=(
                        percentages
                    ),
                    scope_columns=(
                        self._scope_columns
                    ),
                    scope_values=(
                        self._scope_values
                    ),
                )
            )

        except Exception as exc:
            self._set_invalid(
                str(exc)
            )
            return

        self._show_preview(
            preview
        )

        changed = any(
            percentages[value]
            != self._initial_percentages[
                value
            ]
            for value in percentages
        )

        if not changed:
            self.status_label.setText(
                "Distribuido: 100.00% | "
                "Distribucion actual. "
                "No existen cambios."
            )

            self.status_label.setStyleSheet(
                "background-color: #F2F4F7; "
                "color: #475467; "
                "border: 1px solid #D0D5DD; "
                "border-radius: 6px; "
                "padding: 8px; "
                "font-weight: 700;"
            )

            self.apply_button.setEnabled(
                False
            )

            return

        self.status_label.setText(
            "Distribuido: 100.00% | "
            "Distribucion valida."
        )

        self.status_label.setStyleSheet(
            "background-color: #ECFDF3; "
            "color: #067647; "
            "border: 1px solid #ABEFC6; "
            "border-radius: 6px; "
            "padding: 8px; "
            "font-weight: 700;"
        )

        self.apply_button.setEnabled(
            True
        )

    def _show_preview(
        self,
        preview,
    ):
        for item in preview.items:
            self._target_items[
                item.value
            ].setText(
                self._money(
                    item.target_total
                )
            )

            difference_item = (
                self._difference_items[
                    item.value
                ]
            )

            difference_item.setText(
                self._difference(
                    item.difference
                )
            )

            variation_item = (
                self._variation_items[
                    item.value
                ]
            )

            variation_item.setText(
                self._percent(
                    item.variation_percent
                )
            )

            self._color_variation(
                difference_item,
                item.difference,
            )

            self._color_variation(
                variation_item,
                item.difference,
            )

    def _show_approximate(
        self,
        percentages,
    ):
        current_total = (
            self._initial_preview
            .current_total
        )

        current_by_value = {
            item.value:
                item.current_total
            for item
            in self._initial_preview.items
        }

        for value, percentage in (
            percentages.items()
        ):
            target = (
                current_total
                * percentage
                / HUNDRED
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

            difference = (
                target
                - current_by_value[value]
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

            self._target_items[
                value
            ].setText(
                self._money(
                    target
                )
            )

            difference_item = (
                self._difference_items[
                    value
                ]
            )

            difference_item.setText(
                self._difference(
                    difference
                )
            )

            self._color_variation(
                difference_item,
                difference,
            )

            current = (
                current_by_value[
                    value
                ]
            )

            variation = (
                None
                if current == ZERO
                else (
                    difference
                    / current
                    * HUNDRED
                ).quantize(
                    CENT,
                    rounding=ROUND_HALF_UP,
                )
            )

            variation_item = (
                self._variation_items[
                    value
                ]
            )

            variation_item.setText(
                self._percent(
                    variation
                )
            )

            self._color_variation(
                variation_item,
                difference,
            )

    def _set_equal(
        self,
    ):
        percentages = (
            build_equal_percentages(
                self._percentage_inputs
                .keys()
            )
        )

        self._set_percentages(
            percentages
        )

    def _restore(
        self,
    ):
        self._set_percentages(
            self._initial_percentages
        )

    def _set_percentages(
        self,
        percentages,
    ):
        for value, widget in (
            self._percentage_inputs
            .items()
        ):
            widget.blockSignals(
                True
            )

            widget.setText(
                f"{percentages[value]:.2f}"
            )

            widget.blockSignals(
                False
            )

        self._refresh_preview()

    def _accept(
        self,
    ):
        try:
            percentages = (
                self._read_percentages()
            )

            self._service.preview(
                dimension=(
                    self._dimension
                ),
                percentages=(
                    percentages
                ),
                scope_columns=(
                    self._scope_columns
                ),
                scope_values=(
                    self._scope_values
                ),
            )

        except Exception as exc:
            self._set_invalid(
                str(exc)
            )
            return

        self.accept()

    def _filter_rows(
        self,
        text,
    ):
        needle = (
            text
            .strip()
            .lower()
        )

        for row_index in range(
            self.table.rowCount()
        ):
            item = self.table.item(
                row_index,
                0,
            )

            value = (
                item.text().lower()
                if item is not None
                else ""
            )

            self.table.setRowHidden(
                row_index,
                bool(
                    needle
                    and
                    needle not in value
                ),
            )

    def _scope_text(
        self,
    ):
        if not self._scope_columns:
            return (
                "Alcance: todo el presupuesto "
                "habilitado."
            )

        details = " / ".join(
            f"{column.replace('_', ' ').title()}"
            f" = {value}"
            for column, value
            in zip(
                self._scope_columns,
                self._scope_values,
            )
        )

        return (
            "Alcance: "
            + details
        )

    def _set_invalid(
        self,
        message,
    ):
        self.status_label.setText(
            message
        )

        self.status_label.setStyleSheet(
            "background-color: #FEF3F2; "
            "color: #B42318; "
            "border: 1px solid #FECDCA; "
            "border-radius: 6px; "
            "padding: 8px; "
            "font-weight: 700;"
        )

        self.apply_button.setEnabled(
            False
        )

    def _set_warning(
        self,
        message,
    ):
        self.status_label.setText(
            message
        )

        self.status_label.setStyleSheet(
            "background-color: #FFF4E5; "
            "color: #92400E; "
            "border: 1px solid #F3D3A3; "
            "border-radius: 6px; "
            "padding: 8px; "
            "font-weight: 700;"
        )

        self.apply_button.setEnabled(
            False
        )

    @staticmethod
    def _money(
        value,
    ):
        return (
            f"US$ {value:,.2f}"
        )

    @staticmethod
    def _difference(
        value,
    ):
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
    def _percent(
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
    def _color_variation(
        item,
        difference,
    ):
        if difference > ZERO:
            color = QColor(
                "#B42318"
            )

        elif difference < ZERO:
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
