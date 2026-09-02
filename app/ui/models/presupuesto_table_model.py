from decimal import Decimal

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
)

from app.config.presupuesto_schema import (
    AMOUNT_COLUMNS,
)
from app.models.page_result import PageResult


class PresupuestoTableModel(
    QAbstractTableModel
):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._rows = ()
        self._columns = ()

        self._amount_columns = set(
            AMOUNT_COLUMNS
        )

    def set_page(
        self,
        page: PageResult,
    ):
        self.beginResetModel()

        self._rows = page.rows
        self._columns = page.columns

        self.endResetModel()

    def clear(self):
        self.beginResetModel()

        self._rows = ()
        self._columns = ()

        self.endResetModel()

    def rowCount(
        self,
        parent=QModelIndex(),
    ):
        if parent.isValid():
            return 0

        return len(self._rows)

    def columnCount(
        self,
        parent=QModelIndex(),
    ):
        if parent.isValid():
            return 0

        return len(self._columns)

    def data(
        self,
        index,
        role=Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return None

        row = self._rows[
            index.row()
        ]

        column = self._columns[
            index.column()
        ]

        value = row.get(column)

        if role == Qt.ItemDataRole.DisplayRole:
            if value is None:
                return ""

            if isinstance(value, Decimal):
                return f"{value:,.2f}"

            return str(value)

        if role == Qt.ItemDataRole.UserRole:
            return value

        if (
            role
            == Qt.ItemDataRole.TextAlignmentRole
            and column in self._amount_columns
        ):
            return (
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

        return None

    def headerData(
        self,
        section,
        orientation,
        role=Qt.ItemDataRole.DisplayRole,
    ):
        if (
            role
            != Qt.ItemDataRole.DisplayRole
        ):
            return None

        if (
            orientation
            == Qt.Orientation.Horizontal
        ):
            if (
                0
                <= section
                < len(self._columns)
            ):
                return (
                    self._columns[section]
                    .replace("_", " ")
                    .upper()
                )

        return section + 1