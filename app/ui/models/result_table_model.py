from decimal import Decimal

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
)
from PySide6.QtGui import QColor


class ResultTableModel(
    QAbstractTableModel
):
    USD_BACKGROUND = QColor(
        "#EEF8F1"
    )

    def __init__(self, parent=None):
        super().__init__(parent)

        self._rows = ()
        self._columns = ()

    def set_data(
        self,
        rows,
        columns,
    ):
        self.beginResetModel()

        self._rows = tuple(rows)
        self._columns = tuple(columns)

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

    def row_dict(
        self,
        row_index: int,
    ):
        if not (
            0
            <= row_index
            < len(self._rows)
        ):
            raise IndexError(
                "Fila fuera de rango."
            )

        return dict(
            self._rows[row_index]
        )

    def column_name(
        self,
        column_index: int,
    ) -> str:
        if not (
            0
            <= column_index
            < len(self._columns)
        ):
            raise IndexError(
                "Columna fuera de rango."
            )

        return self._columns[
            column_index
        ]

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

            if (
                isinstance(value, int)
                and column == "registros"
            ):
                return f"{value:,}"

            return str(value)

        if role == Qt.ItemDataRole.UserRole:
            return value

        if role == Qt.ItemDataRole.BackgroundRole:
            if (
                column.endswith("_usd")
                or column == "total_usd"
            ):
                return self.USD_BACKGROUND

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if isinstance(
                value,
                (int, Decimal),
            ):
                return (
                    Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter
                )

        if role == Qt.ItemDataRole.ToolTipRole:
            if column.endswith("_usd"):
                return (
                    "Doble clic para modificar "
                    "este total agrupado."
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