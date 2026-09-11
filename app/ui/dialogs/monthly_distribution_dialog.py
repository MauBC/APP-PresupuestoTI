from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
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
PERCENT_CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")


def _decimal(
    value,
) -> Decimal:
    if value is None:
        return ZERO

    if isinstance(
        value,
        Decimal,
    ):
        return value

    return Decimal(
        str(value)
    )


def build_current_percentages(
    row,
    month_columns,
):
    columns = tuple(
        month_columns
    )

    result = {
        column: ZERO
        for column in columns
    }

    editable = [
        column
        for column in columns
        if row.get(column) is not None
    ]

    if not editable:
        return result

    amounts = {
        column: _decimal(
            row.get(column)
        )
        for column in editable
    }

    total = sum(
        amounts.values(),
        ZERO,
    )

    if total == ZERO:
        return result

    for column in editable:
        result[column] = (
            amounts[column]
            / total
            * HUNDRED
        ).quantize(
            PERCENT_CENT,
            rounding=ROUND_HALF_UP,
        )

    residual = (
        HUNDRED
        - sum(
            result[column]
            for column in editable
        )
    ).quantize(
        PERCENT_CENT,
        rounding=ROUND_HALF_UP,
    )

    if residual != ZERO:
        correction_column = max(
            editable,
            key=lambda column: abs(
                amounts[column]
            ),
        )

        result[
            correction_column
        ] += residual

    return result


def build_equal_percentages(
    row,
    month_columns,
):
    columns = tuple(
        month_columns
    )

    result = {
        column: ZERO
        for column in columns
    }

    editable = [
        column
        for column in columns
        if row.get(column) is not None
    ]

    if not editable:
        return result

    base = (
        HUNDRED
        / Decimal(
            len(editable)
        )
    ).quantize(
        PERCENT_CENT,
        rounding=ROUND_HALF_UP,
    )

    for column in editable:
        result[column] = base

    residual = (
        HUNDRED
        - sum(
            result[column]
            for column in editable
        )
    ).quantize(
        PERCENT_CENT,
        rounding=ROUND_HALF_UP,
    )

    result[
        editable[-1]
    ] += residual

    return result


class MonthlyDistributionDialog(
    QDialog
):
    def __init__(
        self,
        *,
        row,
        module_config,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._row = dict(
            row
        )

        self._config = (
            module_config
        )

        self._month_columns = tuple(
            module_config.month_columns
        )

        self._annual_column = (
            module_config.annual_column
        )

        self._initial_percentages = (
            build_current_percentages(
                self._row,
                self._month_columns,
            )
        )

        self._percent_inputs = {}
        self._amount_items = {}

        self.setObjectName(
            "monthlyDistributionDialog"
        )

        self.setWindowTitle(
            "Distribucion mensual "
            f"{module_config.label}"
        )

        self.resize(
            720,
            700,
        )

        self._apply_style()
        self._setup_ui()

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#monthlyDistributionDialog {
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
                border-radius: 5px;
                padding: 7px 9px;
            }

            QLineEdit:focus {
                border: 2px solid #2F7650;
            }

            QLineEdit:disabled {
                background-color: #F2F4F7;
                color: #98A2B3;
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
                border: 0px;
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

            QPushButton#applyDistributionButton {
                background-color: #2F7650;
                color: #FFFFFF;
                border-color: #2F7650;
                font-weight: 700;
            }

            QPushButton#applyDistributionButton:disabled {
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
            "Distribucion mensual "
            f"{self._config.label}"
        )

        title.setStyleSheet(
            "font-size: 20px; "
            "font-weight: 700;"
        )

        layout.addWidget(
            title
        )

        description = QLabel(
            "Define que porcentaje del "
            "presupuesto anual corresponde "
            "a cada mes. La suma debe ser "
            "exactamente 100%."
        )

        description.setWordWrap(
            True
        )

        description.setStyleSheet(
            "color: #667085;"
        )

        layout.addWidget(
            description
        )

        annual_layout = QHBoxLayout()

        annual_layout.addWidget(
            QLabel(
                "Presupuesto anual:"
            )
        )

        self.annual_input = (
            QLineEdit()
        )

        annual_value = _decimal(
            self._row.get(
                self._annual_column
            )
        )

        self.annual_input.setText(
            f"{annual_value:.2f}"
        )

        annual_layout.addWidget(
            self.annual_input,
            1,
        )

        layout.addLayout(
            annual_layout
        )

        self.table = QTableWidget(
            len(
                self._month_columns
            ),
            3,
        )

        self.table.setHorizontalHeaderLabels(
            [
                "MES",
                "PORCENTAJE",
                "IMPORTE",
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

        for (
            row_index,
            column,
        ) in enumerate(
            self._month_columns
        ):
            month_item = (
                QTableWidgetItem(
                    self._month_label(
                        column
                    )
                )
            )

            self.table.setItem(
                row_index,
                0,
                month_item,
            )

            percentage_input = (
                QLineEdit()
            )

            percentage_input.setText(
                f"{self._initial_percentages[column]:.2f}"
            )

            available = (
                self._row.get(
                    column
                )
                is not None
            )

            percentage_input.setEnabled(
                available
            )

            if not available:
                percentage_input.setText(
                    "0.00"
                )

            self._percent_inputs[
                column
            ] = percentage_input

            self.table.setCellWidget(
                row_index,
                1,
                percentage_input,
            )

            amount_item = (
                QTableWidgetItem()
            )

            self._amount_items[
                column
            ] = amount_item

            self.table.setItem(
                row_index,
                2,
                amount_item,
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

        header.setSectionResizeMode(
            1,
            QHeaderView
            .ResizeMode
            .ResizeToContents,
        )

        header.setSectionResizeMode(
            2,
            QHeaderView
            .ResizeMode
            .ResizeToContents,
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

        self.cancel_button = QPushButton(
            "Cancelar"
        )

        self.apply_button = QPushButton(
            "Aplicar distribucion"
        )

        self.apply_button.setObjectName(
            "applyDistributionButton"
        )

        self.apply_button.setEnabled(
            False
        )

        buttons.addWidget(
            self.cancel_button
        )

        buttons.addWidget(
            self.apply_button
        )

        layout.addLayout(
            buttons
        )

        self.annual_input.textChanged.connect(
            self._refresh_preview
        )

        self.equal_button.clicked.connect(
            self._set_equal_distribution
        )

        self.restore_button.clicked.connect(
            self._restore_current
        )

        self.cancel_button.clicked.connect(
            self.reject
        )

        self.apply_button.clicked.connect(
            self._accept_distribution
        )

        self._refresh_preview()

    def percentages(
        self,
    ):
        return self._read_percentages()

    def annual_total(
        self,
    ):
        return self._read_annual_total()

    def _read_annual_total(
        self,
    ):
        text = (
            self.annual_input
            .text()
            .strip()
            .replace("US$", "")
            .replace("$", "")
            .replace(",", "")
            .replace(" ", "")
        )

        if not text:
            raise ValueError(
                "El presupuesto anual "
                "no puede estar vacio."
            )

        try:
            value = Decimal(
                text
            )

        except InvalidOperation as exc:
            raise ValueError(
                "El presupuesto anual "
                "no es valido."
            ) from exc

        value = value.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if value < ZERO:
            raise ValueError(
                "El presupuesto anual "
                "no puede ser negativo."
            )

        return value

    def _read_percentages(
        self,
    ):
        result = {}

        for column in (
            self._month_columns
        ):
            widget = (
                self._percent_inputs[
                    column
                ]
            )

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
                value = Decimal(
                    text
                )

            except InvalidOperation as exc:
                raise ValueError(
                    "Existe un porcentaje "
                    "no valido."
                ) from exc

            value = value.quantize(
                PERCENT_CENT,
                rounding=ROUND_HALF_UP,
            )

            if value < ZERO:
                raise ValueError(
                    "Los porcentajes no "
                    "pueden ser negativos."
                )

            result[column] = value

        return result

    def _refresh_preview(
        self,
        *_,
    ):
        try:
            annual_total = (
                self._read_annual_total()
            )

            percentages = (
                self._read_percentages()
            )

        except ValueError as exc:
            self._set_invalid(
                str(exc)
            )
            self._clear_amounts()
            return

        percentage_total = sum(
            percentages.values(),
            ZERO,
        )

        self._set_approximate_amounts(
            annual_total,
            percentages,
        )

        if percentage_total < HUNDRED:
            missing = (
                HUNDRED
                - percentage_total
            )

            self._set_warning(
                "Distribuido: "
                f"{percentage_total:.2f}% | "
                f"Falta {missing:.2f}%."
            )

            return

        if percentage_total > HUNDRED:
            excess = (
                percentage_total
                - HUNDRED
            )

            self._set_invalid(
                "Distribuido: "
                f"{percentage_total:.2f}% | "
                f"Exceso {excess:.2f}%."
            )

            return

        try:
            from app.services.usd_allocation_service import (
                UsdAllocationService,
            )

            result = (
                UsdAllocationService
                .set_percentage_distribution(
                    self._row,
                    percentages,
                    total=annual_total,
                    month_columns=(
                        self._month_columns
                    ),
                    annual_column=(
                        self._annual_column
                    ),
                )
            )

        except Exception as exc:
            self._set_invalid(
                str(exc)
            )
            return

        for column in (
            self._month_columns
        ):
            item = (
                self._amount_items[
                    column
                ]
            )

            value = result.get(
                column
            )

            if value is None:
                item.setText(
                    "-"
                )
            else:
                item.setText(
                    f"US$ {value:,.2f}"
                )

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

    def _set_approximate_amounts(
        self,
        annual_total,
        percentages,
    ):
        for column in (
            self._month_columns
        ):
            item = (
                self._amount_items[
                    column
                ]
            )

            if self._row.get(
                column
            ) is None:
                item.setText(
                    "-"
                )
                continue

            amount = (
                annual_total
                * percentages[column]
                / HUNDRED
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

            item.setText(
                f"US$ {amount:,.2f}"
            )

    def _clear_amounts(
        self,
    ):
        for column in (
            self._month_columns
        ):
            self._amount_items[
                column
            ].setText(
                "-"
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

    def _set_equal_distribution(
        self,
    ):
        percentages = (
            build_equal_percentages(
                self._row,
                self._month_columns,
            )
        )

        self._set_percentages(
            percentages
        )

    def _restore_current(
        self,
    ):
        annual_value = _decimal(
            self._row.get(
                self._annual_column
            )
        )

        self.annual_input.setText(
            f"{annual_value:.2f}"
        )

        self._set_percentages(
            self._initial_percentages
        )

    def _set_percentages(
        self,
        percentages,
    ):
        for column in (
            self._month_columns
        ):
            widget = (
                self._percent_inputs[
                    column
                ]
            )

            widget.blockSignals(
                True
            )

            widget.setText(
                f"{percentages[column]:.2f}"
            )

            widget.blockSignals(
                False
            )

        self._refresh_preview()

    def _accept_distribution(
        self,
    ):
        try:
            annual_total = (
                self._read_annual_total()
            )

            percentages = (
                self._read_percentages()
            )

            from app.services.usd_allocation_service import (
                UsdAllocationService,
            )

            (
                UsdAllocationService
                .set_percentage_distribution(
                    self._row,
                    percentages,
                    total=annual_total,
                    month_columns=(
                        self._month_columns
                    ),
                    annual_column=(
                        self._annual_column
                    ),
                )
            )

        except Exception as exc:
            self._set_invalid(
                str(exc)
            )
            return

        self.accept()

    @staticmethod
    def _month_label(
        column,
    ):
        return (
            column
            .replace("_usd", "")
            .replace("_", " ")
            .title()
        )
