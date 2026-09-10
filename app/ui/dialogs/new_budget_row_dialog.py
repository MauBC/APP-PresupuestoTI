
from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QIntValidator,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


SPECIAL_LABELS = {
    "anio": "Anio",
    "pais": "Pais",
    "ceco": "CECO",
    "codigo_ceco": "Codigo CECO",
    "codigo_cebe": "Codigo CEBE",
    "gyp": "GyP",
    "desc_cebe": "Desc CEBE",
    "vp_aprobador": "VP Aprobador",
    "u_productiva_cg": "U. Productiva CG",
    "seg_rs": "Seg Rs",
    "moneda_facturacion":
        "Moneda de facturacion",
}


def format_dimension_label(
    column: str,
) -> str:
    if column in SPECIAL_LABELS:
        return SPECIAL_LABELS[
            column
        ]

    return (
        column
        .replace("_", " ")
        .title()
    )


def parse_dimension_value(
    value,
    value_type: str,
):
    text = str(
        value
        if value is not None
        else ""
    ).strip()

    if not text:
        return None

    normalized_type = str(
        value_type
        if value_type is not None
        else "STRING"
    ).strip().upper()

    if normalized_type == "INTEGER":
        try:
            return int(
                text
            )

        except ValueError as exc:
            raise ValueError(
                "Debe ingresar un "
                "numero entero."
            ) from exc

    return text


class NewBudgetRowDialog(
    QDialog
):
    def __init__(
        self,
        *,
        module_config,
        catalogs=None,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._config = (
            module_config
        )

        self._catalogs = {
            column:
                tuple(values)
            for column, values
            in dict(
                catalogs or {}
            ).items()
        }

        self._inputs = {}
        self._dimensions = None

        self.setObjectName(
            "newBudgetRowDialog"
        )

        self.setWindowTitle(
            "Nueva fila "
            f"{self._config.label}"
        )

        self.resize(
            760,
            760,
        )

        self.setMinimumSize(
            620,
            560,
        )

        self._apply_style()
        self._setup_ui()

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#newBudgetRowDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QLabel {
                color: #1F2937;
            }

            QLabel#newRowTitle {
                font-size: 21px;
                font-weight: 700;
            }

            QLabel#newRowSubtitle {
                color: #667085;
                font-size: 12px;
            }

            QLabel#newRowNotice {
                background-color: #FFF4E5;
                color: #92400E;
                border: 1px solid #F3D3A3;
                border-radius: 6px;
                padding: 9px;
            }

            QLabel#newRowStatus {
                border-radius: 6px;
                padding: 8px;
            }

            QLineEdit,
            QComboBox {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #98A2B3;
                border-radius: 6px;
                padding: 7px 9px;
                min-height: 20px;
            }

            QLineEdit:focus,
            QComboBox:focus {
                border: 2px solid #2F7650;
            }

            QScrollArea {
                border: 1px solid #D8DEE4;
                border-radius: 7px;
                background-color: #FFFFFF;
            }

            QFrame#formContainer {
                background-color: #FFFFFF;
            }

            QPushButton {
                background-color: #F2F4F7;
                color: #1F2937;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 9px 18px;
                min-width: 100px;
            }

            QPushButton:hover {
                border-color: #2F7650;
                color: #2F7650;
            }

            QPushButton#newRowCreateButton {
                background-color: #2F7650;
                color: #FFFFFF;
                border-color: #2F7650;
                font-weight: 700;
            }

            QPushButton#newRowCreateButton:hover {
                background-color: #285F42;
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
            "Nueva fila "
            f"{self._config.label}"
        )

        title.setObjectName(
            "newRowTitle"
        )

        subtitle = QLabel(
            "Crea una nueva fila dentro "
            "del Workspace local."
        )

        subtitle.setObjectName(
            "newRowSubtitle"
        )

        notice = QLabel(
            "Este es el formulario base. "
            "Todavia no contiene las reglas "
            "automaticas del negocio. "
            "Los importes se crean en 0 y "
            "pueden editarse despues desde "
            "la tabla o Distribuir meses. "
            "BigQuery no cambia hasta usar "
            "Aplicar cambios."
        )

        notice.setObjectName(
            "newRowNotice"
        )

        notice.setWordWrap(
            True
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        layout.addWidget(
            notice
        )

        scroll = QScrollArea()

        scroll.setWidgetResizable(
            True
        )

        form_container = QFrame()

        form_container.setObjectName(
            "formContainer"
        )

        form = QFormLayout(
            form_container
        )

        form.setContentsMargins(
            18,
            18,
            18,
            18,
        )

        form.setHorizontalSpacing(
            18
        )

        form.setVerticalSpacing(
            10
        )

        type_map = (
            self._config
            .insert_type_map
        )

        for column in (
            self._config
            .dimension_columns
        ):
            value_type = (
                type_map.get(
                    column,
                    "STRING",
                )
            )

            widget = (
                self._create_input(
                    column,
                    value_type,
                )
            )

            self._inputs[
                column
            ] = widget

            label = QLabel(
                format_dimension_label(
                    column
                )
                + ":"
            )

            form.addRow(
                label,
                widget,
            )

        scroll.setWidget(
            form_container
        )

        layout.addWidget(
            scroll,
            1,
        )

        self.status_label = QLabel(
            "Completa los datos que "
            "conozcas para la nueva fila."
        )

        self.status_label.setObjectName(
            "newRowStatus"
        )

        self.status_label.setWordWrap(
            True
        )

        layout.addWidget(
            self.status_label
        )

        buttons = QHBoxLayout()

        buttons.addStretch()

        cancel_button = QPushButton(
            "Cancelar"
        )

        create_button = QPushButton(
            "Crear fila local"
        )

        create_button.setObjectName(
            "newRowCreateButton"
        )

        cancel_button.clicked.connect(
            self.reject
        )

        create_button.clicked.connect(
            self._validate_and_accept
        )

        buttons.addWidget(
            cancel_button
        )

        buttons.addWidget(
            create_button
        )

        layout.addLayout(
            buttons
        )

    def _create_input(
        self,
        column,
        value_type,
    ):
        normalized_type = (
            str(value_type)
            .strip()
            .upper()
        )

        if normalized_type == "INTEGER":
            widget = QLineEdit()

            validator = QIntValidator(
                0,
                2147483647,
                widget,
            )

            widget.setValidator(
                validator
            )

            widget.setPlaceholderText(
                "Numero entero"
            )

            return widget

        values = (
            self._catalogs.get(
                column,
                ()
            )
        )

        if values:
            combo = QComboBox()

            combo.setEditable(
                True
            )

            combo.setInsertPolicy(
                QComboBox
                .InsertPolicy
                .NoInsert
            )

            combo.addItem(
                ""
            )

            combo.addItems(
                [
                    str(value)
                    for value in values
                ]
            )

            completer = (
                combo.completer()
            )

            if completer is not None:
                completer.setCaseSensitivity(
                    Qt.CaseSensitivity
                    .CaseInsensitive
                )

                completer.setFilterMode(
                    Qt.MatchFlag
                    .MatchContains
                )

            combo.setCurrentIndex(
                0
            )

            return combo

        widget = QLineEdit()

        widget.setPlaceholderText(
            "Valor opcional"
        )

        return widget

    def dimensions(
        self,
    ):
        if self._dimensions is None:
            raise RuntimeError(
                "El formulario todavia "
                "no fue validado."
            )

        return dict(
            self._dimensions
        )

    def _widget_text(
        self,
        widget,
    ):
        if isinstance(
            widget,
            QComboBox,
        ):
            return (
                widget.currentText()
            )

        return widget.text()

    def _validate_and_accept(
        self,
    ):
        result = {}

        type_map = (
            self._config
            .insert_type_map
        )

        try:
            for column in (
                self._config
                .dimension_columns
            ):
                widget = (
                    self._inputs[
                        column
                    ]
                )

                value_type = (
                    type_map.get(
                        column,
                        "STRING",
                    )
                )

                try:
                    value = (
                        parse_dimension_value(
                            self._widget_text(
                                widget
                            ),
                            value_type,
                        )
                    )

                except ValueError as exc:
                    raise ValueError(
                        f"{format_dimension_label(column)}: "
                        f"{exc}"
                    ) from exc

                result[
                    column
                ] = value

        except ValueError as exc:
            self._set_error(
                str(exc)
            )
            return

        has_content = any(
            value is not None
            for value in result.values()
        )

        if not has_content:
            self._set_error(
                "Ingresa al menos un dato "
                "para crear la fila."
            )
            return

        self._dimensions = (
            result
        )

        self.accept()

    def _set_error(
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
