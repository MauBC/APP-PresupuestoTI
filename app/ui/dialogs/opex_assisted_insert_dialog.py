from PySide6.QtWidgets import (
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

        self._inputs = {}

        self.setObjectName(
            "opexAssistedInsertDialog"
        )

        self.setWindowTitle(
            "Alta asistida OPEX"
        )

        self.setMinimumSize(
            760,
            620,
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
            "Indica Presupuestador y Origen. "
            "Luego proporciona al menos Gasto, "
            "Proveedor o CECO para consultar "
            "relaciones historicas."
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
            *INFERENCE_DIMENSIONS,
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

        self.analysis_button = QPushButton(
            "Analizar coincidencias"
        )

        self.analysis_button.setObjectName(
            "analyzeButton"
        )

        self.analysis_button.clicked.connect(
            self._analyze
        )

        layout.addWidget(
            self.analysis_button
        )

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
            "El resultado de la inferencia "
            "aparecera aqui."
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
