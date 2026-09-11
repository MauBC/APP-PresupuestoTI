from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


DETAIL_COLUMNS = (
    "TIPO",
    "ROW ID",
    "CAMPO",
    "ANTES",
    "DESPUES",
    "VERSION ANTES",
    "VERSION DESPUES",
    "ACTOR",
    "FECHA",
)


CONTEXT_LABELS = {
    "presupuestador":
        "PRESUPUESTADOR",

    "pais":
        "PAIS",

    "compania":
        "COMPANIA",

    "proveedor":
        "PROVEEDOR",

    "nombre_gasto":
        "NOMBRE DEL GASTO",

    "ceco":
        "CECO",

    "responsable":
        "RESPONSABLE",

    "sociedad":
        "SOCIEDAD",

    "nombre_inversion":
        "NOMBRE DE INVERSION",

    "tipo_capex":
        "TIPO CAPEX",

    "codigo_cebe":
        "CODIGO CEBE",

    "codigo_ceco":
        "CODIGO CECO",
}


def format_context_column(
    column,
) -> str:
    value = str(
        column
        if column is not None
        else ""
    ).strip()

    return CONTEXT_LABELS.get(
        value,
        value.replace(
            "_",
            " ",
        ).upper(),
    )


def format_context_value(
    value,
) -> str:
    if value is None:
        return "(Sin valor)"

    value = str(
        value
    ).strip()

    if not value:
        return "(Sin valor)"

    return value


def detail_context_columns(
    detail,
):
    return tuple(
        getattr(
            detail,
            "context_columns",
            (),
        )
        or ()
    )


def build_detail_headers(
    detail,
):
    return (
        "TIPO",
        *(
            format_context_column(
                column
            )
            for column
            in detail_context_columns(
                detail
            )
        ),
        "CAMPO",
        "ANTES",
        "DESPUES",
        "VERSION ANTES",
        "VERSION DESPUES",
        "ACTOR",
        "FECHA",
        "ROW ID",
    )


def format_detail_datetime(
    value,
) -> str:
    if value is None:
        return ""

    if not isinstance(
        value,
        datetime,
    ):
        return str(value)

    if (
        value.tzinfo is not None
        and value.utcoffset() is not None
    ):
        value = value.astimezone()

    return value.strftime(
        "%d/%m/%Y %H:%M:%S"
    )


def format_audit_value(
    value,
) -> str:
    if value is None:
        return ""

    return str(value)


def format_audit_field(
    column,
) -> str:
    value = str(
        column
        if column is not None
        else ""
    ).strip()

    if value == "habilitado":
        return "Estado"

    parts = [
        part
        for part in value.split("_")
        if part
    ]

    if parts and parts[0].lower() in {
        "anio",
        "ano",
    }:
        parts = [
            "total",
            "anual",
            *parts[1:],
        ]

    result = []

    for part in parts:
        if part.lower() == "usd":
            result.append("USD")
        else:
            result.append(
                part.capitalize()
            )

    return " ".join(result)


def format_audit_display(
    value,
    value_type,
    column,
) -> str:
    if value is None:
        return ""

    kind = str(
        value_type
        if value_type is not None
        else ""
    ).strip().upper()

    text = str(value).strip()

    if kind == "BOOLEAN":
        lowered = text.lower()

        if lowered == "true":
            return "Habilitado"

        if lowered == "false":
            return "Deshabilitado"

    if (
        kind == "NUMERIC"
        and "usd" in str(column).lower()
    ):
        try:
            number = float(text)

            return (
                f"US$ {number:,.2f}"
            )

        except (
            TypeError,
            ValueError,
        ):
            pass

    return text


def audit_change_type_code(
    change,
    batch=None,
) -> str:
    if (
        batch is not None
        and getattr(
            batch,
            "reverted_batch_id",
            None,
        )
    ):
        return "REVERSAL"

    if (
        getattr(
            change,
            "version_before",
            None,
        )
        == 0
    ):
        return "NEW"

    if (
        str(
            getattr(
                change,
                "column_name",
                "",
            )
        ).strip().lower()
        == "habilitado"
    ):
        before = str(
            getattr(
                change,
                "before_value",
                "",
            )
            or ""
        ).strip().lower()

        after = str(
            getattr(
                change,
                "after_value",
                "",
            )
            or ""
        ).strip().lower()

        if (
            before == "true"
            and after == "false"
        ):
            return "DISABLED"

        if (
            before == "false"
            and after == "true"
        ):
            return "REACTIVATED"

    return "EDITED"


def format_audit_change_type(
    change,
    batch=None,
) -> str:
    labels = {
        "EDITED": "Editado",
        "NEW": "Nueva fila",
        "DISABLED": "Deshabilitado",
        "REACTIVATED": "Reactivado",
        "REVERSAL": "Reversion",
    }

    code = audit_change_type_code(
        change,
        batch,
    )

    return labels.get(
        code,
        code,
    )


# Mantiene el contrato historico usado
# por los tests anteriores.
def build_detail_rows(
    detail,
):
    return tuple(
        (
            change.row_id,
            change.column_name,
            format_audit_value(
                change.before_value
            ),
            format_audit_value(
                change.after_value
            ),
            change.version_before,
            change.version_after,
            change.actor,
            format_detail_datetime(
                change.changed_at
            ),
        )
        for change in detail.changes
    )


def build_enhanced_detail_rows(
    detail,
):
    batch = detail.batch

    context_columns = (
        detail_context_columns(
            detail
        )
    )

    rows = []

    for change in detail.changes:

        context_values = []

        for column in context_columns:

            value = (
                detail.context_value(
                    change.row_id,
                    column,
                    "(No disponible)",
                )
            )

            context_values.append(
                format_context_value(
                    value
                )
            )

        type_code = (
            audit_change_type_code(
                change,
                batch,
            )
        )

        rows.append(
            (
                format_audit_change_type(
                    change,
                    batch,
                ),

                *context_values,

                format_audit_field(
                    change.column_name
                ),

                format_audit_display(
                    change.before_value,
                    change.value_type,
                    change.column_name,
                ),

                format_audit_display(
                    change.after_value,
                    change.value_type,
                    change.column_name,
                ),

                change.version_before,
                change.version_after,
                change.actor,

                format_detail_datetime(
                    change.changed_at
                ),

                change.row_id,
                type_code,
            )
        )

    return tuple(
        rows
    )


class HistoryDetailDialog(QDialog):
    def __init__(
        self,
        detail,
        parent=None,
    ):
        super().__init__(parent)

        self._detail = detail

        self.setObjectName(
            "historyDetailDialog"
        )

        self.setWindowTitle(
            "Detalle del historial"
        )

        self.resize(
            1500,
            780,
        )

        self.setMinimumSize(
            1000,
            600,
        )

        self._apply_style()
        self._setup_ui()
        self._populate_table()

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#historyDetailDialog {
                background-color: #FFFFFF;
                color: #1F2933;
            }

            QDialog#historyDetailDialog QLabel {
                background-color: transparent;
                color: #1F2933;
            }

            QLabel#historyDetailTitle {
                color: #164D36;
                font-size: 21px;
                font-weight: 700;
            }

            QLabel#historyBatchInfo {
                color: #475467;
                font-size: 12px;
            }

            QLabel#analysisSummary {
                background-color: #EEF7F1;
                color: #155C3D;
                border: 1px solid #D4E8DA;
                border-radius: 7px;
                padding: 10px 14px;
                font-weight: 600;
            }

            QLineEdit,
            QComboBox {
                background-color: #FFFFFF;
                color: #1F2933;
                border: 1px solid #98A2B3;
                border-radius: 6px;
                padding: 7px 9px;
            }

            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F8F9FA;
                color: #1F2933;
                gridline-color: #E5E7EB;
                selection-background-color: #DCEFE4;
                selection-color: #1F2933;
            }

            QHeaderView::section {
                background-color: #EEF1F4;
                color: #344054;
                border: 0px;
                border-right: 1px solid #D8DEE4;
                border-bottom: 1px solid #D8DEE4;
                padding: 7px;
                font-weight: 600;
            }
            """
        )

    def _setup_ui(
        self,
    ):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            24,
            22,
            24,
            22,
        )

        layout.setSpacing(12)

        title = QLabel(
            "Detalle del batch"
        )

        title.setObjectName(
            "historyDetailTitle"
        )

        layout.addWidget(title)

        batch = self._detail.batch

        relation = ""

        if batch.reverted_batch_id:
            relation = (
                " | Revierte batch: "
                f"{batch.reverted_batch_id}"
            )

        elif getattr(
            batch,
            "reversal_batch_id",
            None,
        ):
            relation = (
                " | Revertido por: "
                f"{batch.reversal_batch_id}"
            )

        info = QLabel(
            f"Batch: {batch.batch_id}"
            f" | Usuario: {batch.actor}"
            f" | Modulo: {batch.budget_module}"
            f" | Estado: {batch.status}"
            f"{relation}"
        )

        info.setObjectName(
            "historyBatchInfo"
        )

        info.setWordWrap(True)

        layout.addWidget(info)

        integrity = (
            "OK"
            if (
                self._detail.field_count_matches
                and
                self._detail.row_count_matches
            )
            else "REVISAR"
        )

        summary = QLabel(
            f"Filas: "
            f"{batch.row_count:,}"
            f" | Campos declarados: "
            f"{batch.field_count:,}"
            f" | Auditorias: "
            f"{self._detail.audit_count:,}"
            f" | Integridad: {integrity}"
        )

        summary.setObjectName(
            "analysisSummary"
        )

        layout.addWidget(summary)

        filters = QHBoxLayout()

        filters.addWidget(
            QLabel("Buscar:")
        )

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "Responsable, presupuestador, "
            "proveedor, gasto, inversion, "
            "CECO, campo o valor..."
        )

        filters.addWidget(
            self.search_input,
            1,
        )

        filters.addWidget(
            QLabel("Tipo:")
        )

        self.type_combo = QComboBox()

        self.type_combo.addItem(
            "Todos",
            "ALL",
        )

        self.type_combo.addItem(
            "Editados",
            "EDITED",
        )

        self.type_combo.addItem(
            "Nuevas filas",
            "NEW",
        )

        self.type_combo.addItem(
            "Deshabilitados",
            "DISABLED",
        )

        self.type_combo.addItem(
            "Reactivados",
            "REACTIVATED",
        )

        self.type_combo.addItem(
            "Reversion",
            "REVERSAL",
        )

        filters.addWidget(
            self.type_combo
        )

        layout.addLayout(filters)

        self._headers = (
            build_detail_headers(
                self._detail
            )
        )

        self.table = QTableWidget()

        self.table.setColumnCount(
            len(
                self._headers
            )
        )

        self.table.setHorizontalHeaderLabels(
            self._headers
        )

        self.table.setAlternatingRowColors(
            True
        )

        self.table.setEditTriggers(
            QAbstractItemView
            .EditTrigger
            .NoEditTriggers
        )

        self.table.setSelectionBehavior(
            QAbstractItemView
            .SelectionBehavior
            .SelectRows
        )

        self.table.setSelectionMode(
            QAbstractItemView
            .SelectionMode
            .ExtendedSelection
        )

        self.table.verticalHeader().setVisible(
            False
        )

        header = (
            self.table.horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView
            .ResizeMode
            .Interactive
        )

        widths = {
            "TIPO": 120,
            "RESPONSABLE": 180,
            "PRESUPUESTADOR": 180,
            "PAIS": 110,
            "SOCIEDAD": 180,
            "COMPANIA": 180,
            "PROVEEDOR": 220,
            "NOMBRE DEL GASTO": 260,
            "NOMBRE DE INVERSION": 280,
            "TIPO CAPEX": 160,
            "CECO": 125,
            "CODIGO CECO": 140,
            "CODIGO CEBE": 140,
            "CAMPO": 150,
            "ANTES": 155,
            "DESPUES": 155,
            "VERSION ANTES": 120,
            "VERSION DESPUES": 130,
            "ACTOR": 180,
            "FECHA": 160,
            "ROW ID": 260,
        }

        for index, label in enumerate(
            self._headers
        ):
            header.resizeSection(
                index,
                widths.get(
                    label,
                    150,
                ),
            )

        layout.addWidget(
            self.table,
            1,
        )

        self.filtered_label = QLabel()

        self.filtered_label.setObjectName(
            "tableStatus"
        )

        layout.addWidget(
            self.filtered_label
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox
            .StandardButton
            .Close
        )

        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(buttons)

        self.search_input.textChanged.connect(
            self._apply_filters
        )

        self.type_combo.currentIndexChanged.connect(
            self._apply_filters
        )

    def _populate_table(
        self,
    ):
        rows = build_enhanced_detail_rows(
            self._detail
        )

        self.table.setSortingEnabled(
            False
        )

        self.table.setRowCount(
            len(rows)
        )

        foreground = {
            "EDITED": "#344054",
            "NEW": "#067647",
            "DISABLED": "#92400E",
            "REACTIVATED": "#067647",
            "REVERSAL": "#155C3D",
        }

        background = {
            "EDITED": "#F2F4F7",
            "NEW": "#ECFDF3",
            "DISABLED": "#FFF4E5",
            "REACTIVATED": "#ECFDF3",
            "REVERSAL": "#EEF7F1",
        }

        for row_index, values in enumerate(
            rows
        ):
            display_values = values[:-1]
            type_code = values[-1]

            if (
                len(display_values)
                != len(self._headers)
            ):
                raise RuntimeError(
                    "El detalle historico no "
                    "coincide con sus columnas."
                )

            for column_index, value in enumerate(
                display_values
            ):
                item = QTableWidgetItem(
                    str(value)
                )

                item.setData(
                    Qt.ItemDataRole.UserRole,
                    type_code,
                )

                if column_index == 0:
                    item.setForeground(
                        QColor(
                            foreground.get(
                                type_code,
                                "#344054",
                            )
                        )
                    )

                    item.setBackground(
                        QColor(
                            background.get(
                                type_code,
                                "#F2F4F7",
                            )
                        )
                    )

                if (
                    self._headers[
                        column_index
                    ]
                    in {
                        "VERSION ANTES",
                        "VERSION DESPUES",
                    }
                ):
                    item.setTextAlignment(
                        Qt.AlignmentFlag
                        .AlignCenter
                    )

                self.table.setItem(
                    row_index,
                    column_index,
                    item,
                )

        self.table.setSortingEnabled(
            True
        )

        self._apply_filters()

    def _apply_filters(
        self,
        *_,
    ):
        query = (
            self.search_input
            .text()
            .strip()
            .casefold()
        )

        selected_type = (
            self.type_combo.currentData()
        )

        visible_count = 0

        for row_index in range(
            self.table.rowCount()
        ):
            type_item = self.table.item(
                row_index,
                0,
            )

            type_code = (
                type_item.data(
                    Qt.ItemDataRole.UserRole
                )
                if type_item is not None
                else ""
            )

            type_matches = (
                selected_type == "ALL"
                or
                type_code == selected_type
            )

            values = []

            for column_index in range(
                self.table.columnCount()
            ):
                item = self.table.item(
                    row_index,
                    column_index,
                )

                if item is not None:
                    values.append(
                        item.text()
                    )

            blob = " ".join(
                values
            ).casefold()

            search_matches = (
                not query
                or query in blob
            )

            visible = (
                type_matches
                and search_matches
            )

            self.table.setRowHidden(
                row_index,
                not visible,
            )

            if visible:
                visible_count += 1

        self.filtered_label.setText(
            f"Mostrando "
            f"{visible_count:,} de "
            f"{self.table.rowCount():,} cambios"
        )
