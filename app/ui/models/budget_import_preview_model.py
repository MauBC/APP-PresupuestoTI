
from decimal import Decimal

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
)


def format_import_value(
    value,
) -> str:
    if value is None:
        return ""

    if isinstance(
        value,
        Decimal,
    ):
        return (
            f"{value:,.2f}"
        )

    if isinstance(
        value,
        bool,
    ):
        return (
            "Si"
            if value
            else "No"
        )

    return str(
        value
    )


def import_preview_columns(
    module_config,
):
    return tuple(
        module_config
        .insert_columns
    )


class BudgetImportPreviewModel(
    QAbstractTableModel
):
    def __init__(
        self,
        *,
        rows,
        module_config,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._rows = tuple(
            rows
        )

        self._columns = (
            import_preview_columns(
                module_config
            )
        )

    def rowCount(
        self,
        parent=QModelIndex(),
    ):
        if parent.isValid():
            return 0

        return len(
            self._rows
        )

    def columnCount(
        self,
        parent=QModelIndex(),
    ):
        if parent.isValid():
            return 0

        return len(
            self._columns
        )

    def data(
        self,
        index,
        role=(
            Qt.ItemDataRole
            .DisplayRole
        ),
    ):
        if not index.isValid():
            return None

        row = self._rows[
            index.row()
        ]

        column = self._columns[
            index.column()
        ]

        value = row.get(
            column
        )

        if (
            role
            == Qt.ItemDataRole
            .DisplayRole
        ):
            return format_import_value(
                value
            )

        if (
            role
            == Qt.ItemDataRole
            .UserRole
        ):
            return value

        if (
            role
            == Qt.ItemDataRole
            .TextAlignmentRole
            and isinstance(
                value,
                (
                    Decimal,
                    int,
                    float,
                ),
            )
            and not isinstance(
                value,
                bool,
            )
        ):
            return (
                Qt.AlignmentFlag.AlignRight
                |
                Qt.AlignmentFlag.AlignVCenter
            )

        return None

    def headerData(
        self,
        section,
        orientation,
        role=(
            Qt.ItemDataRole
            .DisplayRole
        ),
    ):
        if (
            role
            != Qt.ItemDataRole
            .DisplayRole
        ):
            return None

        if (
            orientation
            == Qt.Orientation
            .Horizontal
        ):
            if (
                0
                <= section
                < len(
                    self._columns
                )
            ):
                return (
                    self._columns[
                        section
                    ]
                    .replace(
                        "_",
                        " ",
                    )
                    .upper()
                )

        return section + 1


class BudgetImportIssueModel(
    QAbstractTableModel
):
    COLUMNS = (
        (
            "row_number",
            "FILA",
        ),
        (
            "severity",
            "TIPO",
        ),
        (
            "code",
            "CODIGO",
        ),
        (
            "column",
            "COLUMNA",
        ),
        (
            "message",
            "DETALLE",
        ),
        (
            "raw_value",
            "VALOR",
        ),
    )

    def __init__(
        self,
        *,
        issues,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._issues = tuple(
            issues
        )

    def rowCount(
        self,
        parent=QModelIndex(),
    ):
        if parent.isValid():
            return 0

        return len(
            self._issues
        )

    def columnCount(
        self,
        parent=QModelIndex(),
    ):
        if parent.isValid():
            return 0

        return len(
            self.COLUMNS
        )

    def data(
        self,
        index,
        role=(
            Qt.ItemDataRole
            .DisplayRole
        ),
    ):
        if not index.isValid():
            return None

        issue = self._issues[
            index.row()
        ]

        attribute = (
            self.COLUMNS[
                index.column()
            ][0]
        )

        value = getattr(
            issue,
            attribute,
        )

        if attribute == "severity":
            value = value.value

        if (
            role
            == Qt.ItemDataRole
            .DisplayRole
        ):
            return (
                ""
                if value is None
                else str(value)
            )

        if (
            role
            == Qt.ItemDataRole
            .UserRole
        ):
            return value

        return None

    def headerData(
        self,
        section,
        orientation,
        role=(
            Qt.ItemDataRole
            .DisplayRole
        ),
    ):
        if (
            role
            != Qt.ItemDataRole
            .DisplayRole
        ):
            return None

        if (
            orientation
            == Qt.Orientation
            .Horizontal
        ):
            if (
                0
                <= section
                < len(
                    self.COLUMNS
                )
            ):
                return (
                    self.COLUMNS[
                        section
                    ][1]
                )

        return section + 1
