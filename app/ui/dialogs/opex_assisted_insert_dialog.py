from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from app.services.opex_smart_insert_service import (
    OpexSmartInsertService,
)


USER_DIMENSIONS = (
    "presupuestador",
    "origen",
)

INFERENCE_DIMENSIONS = (
    "nombre_gasto",
    "proveedor",
    "ceco",
)

FIELD_LABELS = {
    "presupuestador":
        "Presupuestador",
    "origen":
        "Origen",
    "nombre_gasto":
        "Nombre del gasto",
    "proveedor":
        "Proveedor",
    "ceco":
        "CECO",
}


def _clean_text(
    value,
) -> str:
    if value is None:
        return ""

    return str(
        value
    ).strip()


def build_opex_assisted_base_dimensions(
    values,
) -> dict[str, str]:
    supplied = dict(
        values or {}
    )

    result = {}

    for column in (
        *USER_DIMENSIONS,
        *INFERENCE_DIMENSIONS,
    ):
        clean = _clean_text(
            supplied.get(
                column
            )
        )

        if clean:
            result[
                column
            ] = clean

    missing = [
        FIELD_LABELS[column]
        for column in USER_DIMENSIONS
        if column not in result
    ]

    if missing:
        raise ValueError(
            "Completa los campos obligatorios: "
            + ", ".join(
                missing
            )
            + "."
        )

    if not any(
        column in result
        for column in INFERENCE_DIMENSIONS
    ):
        raise ValueError(
            "Ingresa al menos un dato para "
            "buscar en el historial: "
            "Nombre del gasto, Proveedor "
            "o CECO."
        )

    return result


def build_opex_assisted_inference_values(
    values,
) -> dict[str, str]:
    base = (
        build_opex_assisted_base_dimensions(
            values
        )
    )

    return {
        column:
            base[column]
        for column
        in INFERENCE_DIMENSIONS
        if column in base
    }


def _field_label(
    column,
) -> str:
    return FIELD_LABELS.get(
        column,
        str(column)
        .replace(
            "_",
            " ",
        )
        .title(),
    )


def parse_opex_assisted_allocations(
    text,
):
    rows = []

    raw_text = str(
        text
        if text is not None
        else ""
    )

    for line_number, raw_line in enumerate(
        raw_text.splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        if ";" in line:
            parts = line.split(
                ";",
                1,
            )

        elif "=" in line:
            parts = line.split(
                "=",
                1,
            )

        else:
            raise ValueError(
                "Linea "
                f"{line_number}: usa "
                "CECO;VALOR."
            )

        ceco = parts[0].strip()
        value = parts[1].strip()

        if not ceco:
            raise ValueError(
                "Linea "
                f"{line_number}: "
                "CECO vacio."
            )

        if not value:
            raise ValueError(
                "Linea "
                f"{line_number}: "
                "valor vacio."
            )

        rows.append(
            (
                ceco,
                value,
            )
        )

    if not rows:
        raise ValueError(
            "Ingresa al menos una "
            "distribucion CECO."
        )

    cecos = [
        ceco
        for ceco, _
        in rows
    ]

    duplicates = sorted(
        {
            ceco
            for ceco in cecos
            if cecos.count(
                ceco
            ) > 1
        }
    )

    if duplicates:
        raise ValueError(
            "CECO duplicado: "
            + ", ".join(
                duplicates
            )
            + "."
        )

    return tuple(
        rows
    )


def build_opex_assisted_insert_dimensions(
    values,
):
    supplied = dict(
        values or {}
    )

    result = {}

    for column in (
        "nombre_gasto",
        "proveedor",
    ):
        clean = _clean_text(
            supplied.get(
                column
            )
        )

        if clean:
            result[
                column
            ] = clean

    return result


def build_opex_assisted_row_overrides(
    values,
):
    supplied = dict(
        values or {}
    )

    result = {}

    missing = []

    for column in USER_DIMENSIONS:
        clean = _clean_text(
            supplied.get(
                column
            )
        )

        if not clean:
            missing.append(
                FIELD_LABELS[
                    column
                ]
            )
            continue

        result[
            column
        ] = clean

    if missing:
        raise ValueError(
            "Completa los campos obligatorios: "
            + ", ".join(
                missing
            )
            + "."
        )

    result[
        "periodo"
    ] = "2027 PB"

    return result


def build_opex_assisted_preview_request(
    service,
    *,
    values,
    mode,
    allocations_text,
    annual_total,
    actor,
):
    allocations = (
        parse_opex_assisted_allocations(
            allocations_text
        )
    )

    base_dimensions = (
        build_opex_assisted_insert_dimensions(
            values
        )
    )

    row_overrides = (
        build_opex_assisted_row_overrides(
            values
        )
    )

    normalized_mode = str(
        mode
        if mode is not None
        else ""
    ).strip().upper()

    if normalized_mode == "PERCENTAGE":
        total = _clean_text(
            annual_total
        )

        if not total:
            raise ValueError(
                "Ingresa el total anual "
                "para distribuir por porcentaje."
            )

        return (
            service.preview_percentages(
                base_dimensions=(
                    base_dimensions
                ),
                allocations=allocations,
                annual_total=total,
                actor=actor,
                row_overrides=(
                    row_overrides
                ),
            )
        )

    if normalized_mode == "AMOUNT":
        return (
            service.preview_amounts(
                base_dimensions=(
                    base_dimensions
                ),
                allocations=allocations,
                actor=actor,
                row_overrides=(
                    row_overrides
                ),
            )
        )

    raise ValueError(
        "Modo de distribucion no valido."
    )


def format_opex_assisted_preview(
    preview,
):
    lines = [
        (
            "Modo: "
            f"{preview.mode}"
        ),
        (
            "Total origen: "
            f"US$ {preview.source_total:,.2f}"
        ),
        (
            "Total distribuido: "
            f"US$ {preview.allocated_total:,.2f}"
        ),
        (
            "Filas: "
            f"{preview.row_count}"
        ),
        (
            "Listas: "
            f"{preview.ready_count}"
        ),
        (
            "Bloqueadas: "
            f"{preview.blocked_count}"
        ),
        "",
    ]

    for index, item in enumerate(
        preview.items,
        start=1,
    ):
        state = (
            "LISTO"
            if item.is_ready
            else "BLOQUEADO"
        )

        lines.extend(
            [
                (
                    f"{index}. CECO "
                    f"{item.ceco}"
                ),
                (
                    "   Estado: "
                    f"{state}"
                ),
                (
                    "   Importe anual: "
                    f"US$ "
                    f"{item.annual_total:,.2f}"
                ),
                (
                    "   Coincidencias: "
                    f"{item.matching_row_count}"
                ),
            ]
        )

        if item.blockers:
            lines.append(
                "   Bloqueos: "
                + ", ".join(
                    item.blockers
                )
            )

        if item.ambiguous_values:
            lines.append(
                "   Ambiguedades:"
            )

            for (
                column,
                options,
            ) in (
                item.ambiguous_values
            ):
                lines.append(
                    "      - "
                    f"{_field_label(column)}: "
                    + " | ".join(
                        str(option)
                        for option
                        in options
                    )
                )

        lines.append(
            ""
        )

    return "\n".join(
        lines
    )


def format_opex_assisted_inference(
    result,
) -> str:
    lines = [
        (
            "Coincidencias historicas: "
            f"{result.matching_row_count:,}"
        )
    ]

    if (
        result.matching_row_count
        <= 0
    ):
        lines.extend(
            [
                "",
                (
                    "No se encontro una "
                    "coincidencia historica."
                ),
                (
                    "La alta todavia no puede "
                    "autocompletarse de forma "
                    "segura."
                ),
            ]
        )

        return "\n".join(
            lines
        )

    inferred = tuple(
        (
            column,
            value,
        )
        for column, value
        in result.inferred_values
        if column not in USER_DIMENSIONS
    )

    ambiguous = tuple(
        (
            column,
            options,
        )
        for column, options
        in result.ambiguous_values
        if column not in USER_DIMENSIONS
    )

    no_data = tuple(
        column
        for column
        in result.no_data_columns
        if column not in USER_DIMENSIONS
    )

    lines.extend(
        [
            "",
            "AUTOCOMPLETADO INEQUIVOCO",
        ]
    )

    if inferred:
        for column, value in inferred:
            lines.append(
                f"- {_field_label(column)}: "
                f"{value}"
            )
    else:
        lines.append(
            "- Sin dimensiones adicionales."
        )

    lines.extend(
        [
            "",
            "AMBIGUEDADES",
        ]
    )

    if ambiguous:
        for column, options in ambiguous:
            lines.append(
                f"- {_field_label(column)}: "
                + " | ".join(
                    str(option)
                    for option in options
                )
            )
    else:
        lines.append(
            "- Sin ambiguedades."
        )

    lines.extend(
        [
            "",
            "SIN INFORMACION HISTORICA",
        ]
    )

    if no_data:
        for column in no_data:
            lines.append(
                "- "
                + _field_label(
                    column
                )
            )
    else:
        lines.append(
            "- Ninguna."
        )

    return "\n".join(
        lines
    )


class OpexAssistedInsertDialog(
    QDialog
):
    def __init__(
        self,
        *,
        actor,
        inference_service,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._actor = str(
            actor
        ).strip()

        self._inference_service = (
            inference_service
        )

        self._insert_service = (
            OpexSmartInsertService(
                inference_service
            )
        )

        self._preview = None
        self._inputs = {}

        self.setObjectName(
            "opexAssistedInsertDialog"
        )

        self.setWindowTitle(
            "Alta asistida OPEX"
        )

        self.setMinimumSize(
            820,
            760,
        )

        self._apply_style()
        self._setup_ui()

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#opexAssistedInsertDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QLabel#assistedTitle {
                color: #173F35;
                font-size: 21px;
                font-weight: 700;
            }

            QLabel#assistedSubtitle {
                color: #667085;
                font-size: 12px;
            }

            QFrame#assistedFormPanel {
                background-color: #F8FAF9;
                border: 1px solid #D7E5DD;
                border-radius: 8px;
            }

            QLineEdit {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #B7C9C0;
                border-radius: 6px;
                padding: 8px;
            }

            QLineEdit:focus {
                border: 2px solid #2F7650;
            }

            QComboBox {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #B7C9C0;
                border-radius: 6px;
                padding: 7px 9px;
            }

            QPlainTextEdit {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 8px;
            }

            QPushButton#analyzeButton {
                background-color: #2F7650;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 9px 18px;
                font-weight: 700;
            }

            QPushButton#analyzeButton:hover {
                background-color: #286544;
            }

            QPushButton#closeButton {
                background-color: #FFFFFF;
                color: #344054;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 9px 18px;
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
            14
        )

        title = QLabel(
            "Alta asistida OPEX"
        )

        title.setObjectName(
            "assistedTitle"
        )

        subtitle = QLabel(
            "Indica Presupuestador y Origen, "
            "agrega referencias del gasto si "
            "las conoces y distribuye el total "
            "entre uno o varios CECO."
        )

        subtitle.setObjectName(
            "assistedSubtitle"
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

        snapshot_count = int(
            getattr(
                self._inference_service,
                "snapshot_count",
                0,
            )
            or 0
        )

        history_label = QLabel(
            "Historico disponible: "
            f"{snapshot_count:,} filas OPEX "
            "habilitadas."
        )

        history_label.setObjectName(
            "assistedSubtitle"
        )

        layout.addWidget(
            history_label
        )

        panel = QFrame()

        panel.setObjectName(
            "assistedFormPanel"
        )

        form = QFormLayout(
            panel
        )

        form.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        placeholders = {
            "presupuestador":
                "Dato obligatorio",
            "origen":
                "Dato obligatorio",
            "nombre_gasto":
                "Ej. Licencias",
            "proveedor":
                "Ej. Microsoft",
            "ceco":
                "Conserva ceros iniciales",
        }

        for column in (
            *USER_DIMENSIONS,
            "nombre_gasto",
            "proveedor",
        ):
            input_widget = QLineEdit()

            input_widget.setPlaceholderText(
                placeholders[
                    column
                ]
            )

            self._inputs[
                column
            ] = input_widget

            form.addRow(
                FIELD_LABELS[
                    column
                ] + ":",
                input_widget,
            )

        layout.addWidget(
            panel
        )

        distribution_panel = QFrame()

        distribution_panel.setObjectName(
            "assistedFormPanel"
        )

        distribution_form = QFormLayout(
            distribution_panel
        )

        distribution_form.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        self.allocation_mode_combo = QComboBox()

        self.allocation_mode_combo.addItem(
            "Por porcentaje",
            "PERCENTAGE",
        )

        self.allocation_mode_combo.addItem(
            "Por importe",
            "AMOUNT",
        )

        self.allocation_mode_combo.currentIndexChanged.connect(
            self._allocation_mode_changed
        )

        distribution_form.addRow(
            "Modo:",
            self.allocation_mode_combo,
        )

        self.annual_total_input = QLineEdit()

        self.annual_total_input.setPlaceholderText(
            "Ej. 100000.00"
        )

        distribution_form.addRow(
            "Total anual (USD):",
            self.annual_total_input,
        )

        self.allocations_input = QPlainTextEdit()

        self.allocations_input.setMinimumHeight(
            110
        )

        distribution_form.addRow(
            "CECO ; valor:",
            self.allocations_input,
        )

        allocation_help = QLabel(
            "Usa una linea por CECO. "
            "Ejemplo: 253OP040R2;40"
        )

        allocation_help.setObjectName(
            "assistedSubtitle"
        )

        allocation_help.setWordWrap(
            True
        )

        distribution_form.addRow(
            "",
            allocation_help,
        )

        layout.addWidget(
            distribution_panel
        )

        self.preview_button = QPushButton(
            "Generar vista previa"
        )

        self.preview_button.setObjectName(
            "analyzeButton"
        )

        self.preview_button.clicked.connect(
            self._generate_preview
        )

        layout.addWidget(
            self.preview_button
        )

        self.analysis_button = QPushButton(
            "Analizar referencia historica"
        )

        self.analysis_button.setObjectName(
            "closeButton"
        )

        self.analysis_button.clicked.connect(
            self._analyze
        )

        layout.addWidget(
            self.analysis_button
        )

        self._allocation_mode_changed()

        self.status_label = QLabel(
            "Todavia no se ha realizado "
            "ningun analisis."
        )

        self.status_label.setWordWrap(
            True
        )

        layout.addWidget(
            self.status_label
        )

        self.result_box = QPlainTextEdit()

        self.result_box.setReadOnly(
            True
        )

        self.result_box.setPlaceholderText(
            "La vista previa o el analisis "
            "historico apareceran aqui."
        )

        layout.addWidget(
            self.result_box,
            1,
        )

        actions = QHBoxLayout()

        actions.addStretch()

        close_button = QPushButton(
            "Cerrar"
        )

        close_button.setObjectName(
            "closeButton"
        )

        close_button.clicked.connect(
            self.reject
        )

        actions.addWidget(
            close_button
        )

        layout.addLayout(
            actions
        )

    def _allocation_mode_changed(
        self,
        *_,
    ):
        mode = (
            self.allocation_mode_combo
            .currentData()
        )

        is_percentage = (
            mode == "PERCENTAGE"
        )

        self.annual_total_input.setEnabled(
            is_percentage
        )

        if is_percentage:
            self.annual_total_input.setPlaceholderText(
                "Ej. 100000.00"
            )

            self.allocations_input.setPlaceholderText(
                "253OP040R2;40\n"
                "253OP040R3;35\n"
                "253OP040R4;25"
            )

        else:
            self.annual_total_input.setPlaceholderText(
                "Se calcula automaticamente"
            )

            self.allocations_input.setPlaceholderText(
                "253OP040R2;40000\n"
                "253OP040R3;35000\n"
                "253OP040R4;25000"
            )

        self._preview = None

    def _generate_preview(
        self,
    ):
        try:
            preview = (
                build_opex_assisted_preview_request(
                    self._insert_service,
                    values=self.values(),
                    mode=(
                        self.allocation_mode_combo
                        .currentData()
                    ),
                    allocations_text=(
                        self.allocations_input
                        .toPlainText()
                    ),
                    annual_total=(
                        self.annual_total_input
                        .text()
                    ),
                    actor=self._actor,
                )
            )

        except Exception as exc:
            self._preview = None
            self.result_box.clear()

            self._set_status(
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
                tone="error",
            )

            return

        self._preview = preview

        self.result_box.setPlainText(
            format_opex_assisted_preview(
                preview
            )
        )

        if preview.is_ready:
            self._set_status(
                "Vista previa lista. "
                f"{preview.ready_count:,} fila(s) "
                "pueden generarse de forma segura.",
                tone="success",
            )

        else:
            self._set_status(
                "Vista previa generada, pero "
                f"{preview.blocked_count:,} fila(s) "
                "requieren resolver historial "
                "o ambiguedades.",
                tone="warning",
            )

    def values(
        self,
    ) -> dict[str, str]:
        return {
            column:
                widget.text()
            for column, widget
            in self._inputs.items()
        }

    def _analyze(
        self,
    ):
        try:
            base_dimensions = (
                build_opex_assisted_base_dimensions(
                    self.values()
                )
            )

            inference_values = (
                build_opex_assisted_inference_values(
                    base_dimensions
                )
            )

            result = (
                self._inference_service
                .infer(
                    inference_values
                )
            )

        except Exception as exc:
            self.result_box.clear()

            self._set_status(
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
                tone="error",
            )

            return

        user_context = (
            "DATOS DEFINIDOS POR EL USUARIO\n"
            f"- Presupuestador: "
            f"{base_dimensions['presupuestador']}\n"
            f"- Origen: "
            f"{base_dimensions['origen']}\n\n"
        )

        self.result_box.setPlainText(
            user_context
            + format_opex_assisted_inference(
                result
            )
        )

        if (
            result.matching_row_count
            <= 0
        ):
            self._set_status(
                "No se encontro historial "
                "compatible.",
                tone="warning",
            )

        elif result.ambiguous_values:
            self._set_status(
                "Se encontraron coincidencias, "
                "pero existen dimensiones "
                "ambiguas que deberan resolverse.",
                tone="warning",
            )

        else:
            self._set_status(
                "Analisis completado. "
                "Las relaciones historicas "
                "son revisables abajo.",
                tone="success",
            )

    def _set_status(
        self,
        message,
        *,
        tone,
    ):
        styles = {
            "success": (
                "#ECFDF3",
                "#067647",
                "#ABEFC6",
            ),
            "warning": (
                "#FFF4E5",
                "#92400E",
                "#F3D3A3",
            ),
            "error": (
                "#FEF3F2",
                "#B42318",
                "#FECDCA",
            ),
        }

        background, color, border = (
            styles[
                tone
            ]
        )

        self.status_label.setText(
            str(message)
        )

        self.status_label.setStyleSheet(
            "QLabel {"
            f"background-color: {background};"
            f"color: {color};"
            f"border: 1px solid {border};"
            "border-radius: 6px;"
            "padding: 8px;"
            "font-weight: 700;"
            "}"
        )
