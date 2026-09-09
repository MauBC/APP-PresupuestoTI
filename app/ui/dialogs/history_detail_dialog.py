from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
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
    "ROW ID",
    "CAMPO",
    "ANTES",
    "DESPUES",
    "VERSION ANTES",
    "VERSION DESPUES",
    "ACTOR",
    "FECHA",
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
        return str(
            value
        )

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

    return str(
        value
    )


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
        for change
        in detail.changes
    )


class HistoryDetailDialog(
    QDialog
):
    def __init__(
        self,
        detail,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._detail = detail

        self.setObjectName(
            "historyDetailDialog"
        )

        self.setWindowTitle(
            "Detalle del historial"
        )

        self.resize(
            1180,
            720,
        )

        self.setMinimumSize(
            980,
            580,
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
                font-size: 13px;
            }

            QLabel#analysisSummary {
                background-color: #EEF7F1;
                color: #155C3D;
                border: 1px solid #D4E8DA;
                border-radius: 7px;
                padding: 10px 14px;
                font-weight: 700;
            }

            QLabel#historySearchLabel {
                color: #475467;
                font-weight: 600;
            }

            QLabel#tableStatus {
                color: #667085;
                font-size: 12px;
            }

            QLineEdit {
                background-color: #FFFFFF;
                color: #1F2933;
                border: 1px solid #B8C9BF;
                border-radius: 6px;
                padding: 8px 10px;
                selection-background-color: #DCEFE4;
                selection-color: #164D36;
            }

            QLineEdit:focus {
                border: 2px solid #2F7650;
            }

            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F7FAF8;
                color: #1F2933;
                border: 1px solid #D7E2DB;
                border-radius: 6px;
                gridline-color: #DCE5DF;
                selection-background-color: #DDEFE4;
                selection-color: #164D36;
            }

            QTableWidget::item {
                padding-left: 7px;
                padding-right: 7px;
            }

            QHeaderView::section {
                background-color: #E7F2EB;
                color: #155C3D;
                border: none;
                border-right: 1px solid #D0E0D6;
                border-bottom: 1px solid #C8D9CF;
                padding: 8px 6px;
                font-weight: 700;
            }

            QDialogButtonBox QPushButton {
                background-color: #FFFFFF;
                color: #244D38;
                border: 1px solid #B8C9BF;
                border-radius: 6px;
                min-width: 105px;
                padding: 8px 18px;
                font-weight: 600;
            }

            QDialogButtonBox QPushButton:hover {
                background-color: #EEF6F1;
                border-color: #79A78C;
            }

            QDialogButtonBox QPushButton:pressed {
                background-color: #E1EFE6;
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

        batch = (
            self._detail.batch
        )

        title = QLabel(
            "Detalle de cambios aplicados"
        )

        title.setObjectName(
            "historyDetailTitle"
        )

        layout.addWidget(
            title
        )

        information = QLabel(
            f"Batch: {batch.batch_id}\n"
            f"Usuario: {batch.actor}   |   "
            f"Estado: {batch.status}   |   "
            f"Modulo: {batch.budget_module}"
        )

        information.setObjectName(
            "historyBatchInfo"
        )

        information.setTextInteractionFlags(
            Qt.TextInteractionFlag
            .TextSelectableByMouse
        )

        layout.addWidget(
            information
        )

        counts = QLabel(
            f"{self._detail.audit_count:,} cambios auditados"
            f"   |   "
            f"{self._detail.audited_row_count:,} filas"
        )

        counts.setObjectName(
            "analysisSummary"
        )

        layout.addWidget(
            counts
        )

        search_layout = (
            QHBoxLayout()
        )

        search_label = QLabel(
            "Buscar:"
        )

        search_label.setObjectName(
            "historySearchLabel"
        )

        self.search_input = (
            QLineEdit()
        )

        self.search_input.setPlaceholderText(
            "ROW ID, campo, valor, actor..."
        )

        search_layout.addWidget(
            search_label
        )

        search_layout.addWidget(
            self.search_input,
            1,
        )

        layout.addLayout(
            search_layout
        )

        self.table = (
            QTableWidget()
        )

        self.table.setColumnCount(
            len(
                DETAIL_COLUMNS
            )
        )

        self.table.setHorizontalHeaderLabels(
            DETAIL_COLUMNS
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
            .SingleSelection
        )

        self.table.verticalHeader().setVisible(
            False
        )

        self.table.verticalHeader().setDefaultSectionSize(
            30
        )

        header = (
            self.table
            .horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView
            .ResizeMode
            .Interactive
        )

        widths = (
            275,
            145,
            145,
            145,
            125,
            125,
            185,
            155,
        )

        for index, width in enumerate(
            widths
        ):
            header.resizeSection(
                index,
                width,
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

        buttons = (
            QDialogButtonBox(
                QDialogButtonBox
                .StandardButton
                .Close
            )
        )

        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(
            buttons
        )

        self.search_input.textChanged.connect(
            self._apply_search
        )

    def _populate_table(
        self,
    ):
        rows = build_detail_rows(
            self._detail
        )

        self.table.setSortingEnabled(
            False
        )

        self.table.setRowCount(
            len(rows)
        )

        for row_index, values in enumerate(
            rows
        ):
            for (
                column_index,
                value,
            ) in enumerate(values):
                item = (
                    QTableWidgetItem(
                        str(value)
                    )
                )

                if column_index in (
                    4,
                    5,
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

        self._apply_search(
            ""
        )

    def _apply_search(
        self,
        text,
    ):
        query = str(
            text
            if text is not None
            else ""
        ).strip().casefold()

        visible_count = 0

        for row_index in range(
            self.table.rowCount()
        ):
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

            hidden = bool(
                query
                and query not in blob
            )

            self.table.setRowHidden(
                row_index,
                hidden,
            )

            if not hidden:
                visible_count += 1

        self.filtered_label.setText(
            f"Mostrando "
            f"{visible_count:,} de "
            f"{self.table.rowCount():,} cambios"
        )
