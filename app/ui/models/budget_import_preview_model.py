
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
    INCLUDE_COLUMN = "__include__"
    SOURCE_ROW_COLUMN = "__source_row__"

    def __init__(
        self,
        *,
        rows,
        module_config,
        source_row_numbers=(),
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._rows = tuple(
            dict(row)
            for row in rows
        )

        numbers = tuple(
            source_row_numbers
        )

        if (
            numbers
            and len(numbers)
            != len(
                self._rows
            )
        ):
            raise ValueError(
                "source_row_numbers debe "
                "tener la misma cantidad "
                "que rows."
            )

        if not numbers:
            numbers = tuple(
                range(
                    2,
                    2
                    + len(
                        self._rows
                    ),
                )
            )

        self._source_row_numbers = (
            numbers
        )

        self._included = [
            True
            for _ in self._rows
        ]

        self._business_columns = (
            import_preview_columns(
                module_config
            )
        )

        self._columns = (
            self.INCLUDE_COLUMN,
            self.SOURCE_ROW_COLUMN,
            *self._business_columns,
        )

    @property
    def included_count(
        self,
    ) -> int:
        return sum(
            1
            for value
            in self._included
            if value
        )

    @property
    def excluded_count(
        self,
    ) -> int:
        return (
            len(
                self._included
            )
            - self.included_count
        )

    def included_rows(
        self,
    ):
        return tuple(
            dict(row)
            for row, included
            in zip(
                self._rows,
                self._included,
            )
            if included
        )

    def set_included(
        self,
        row_index,
        included,
    ) -> bool:
        if not (
            0
            <= row_index
            < len(
                self._rows
            )
        ):
            return False

        value = bool(
            included
        )

        if (
            self._included[
                row_index
            ]
            == value
        ):
            return False

        self._included[
            row_index
        ] = value

        index = self.index(
            row_index,
            0,
        )

        self.dataChanged.emit(
            index,
            index,
            [
                Qt.ItemDataRole
                .CheckStateRole,
            ],
        )

        return True

    def include_all(
        self,
    ):
        changed_rows = []

        for index in range(
            len(
                self._included
            )
        ):
            if not (
                self._included[
                    index
                ]
            ):
                self._included[
                    index
                ] = True

                changed_rows.append(
                    index
                )

        if not changed_rows:
            return

        self.dataChanged.emit(
            self.index(
                min(
                    changed_rows
                ),
                0,
            ),
            self.index(
                max(
                    changed_rows
                ),
                0,
            ),
            [
                Qt.ItemDataRole
                .CheckStateRole,
            ],
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

        row_index = (
            index.row()
        )

        column = (
            self._columns[
                index.column()
            ]
        )

        if (
            column
            == self.INCLUDE_COLUMN
        ):
            if (
                role
                == Qt.ItemDataRole
                .CheckStateRole
            ):
                return (
                    Qt.CheckState.Checked
                    if self._included[
                        row_index
                    ]
                    else
                    Qt.CheckState.Unchecked
                )

            if (
                role
                == Qt.ItemDataRole
                .DisplayRole
            ):
                return ""

            return None

        if (
            column
            == self.SOURCE_ROW_COLUMN
        ):
            value = (
                self._source_row_numbers[
                    row_index
                ]
            )

        else:
            value = (
                self._rows[
                    row_index
                ]
                .get(
                    column
                )
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

    def setData(
        self,
        index,
        value,
        role=(
            Qt.ItemDataRole
            .EditRole
        ),
    ):
        if not index.isValid():
            return False

        column = (
            self._columns[
                index.column()
            ]
        )

        if (
            column
            != self.INCLUDE_COLUMN
            or role
            != Qt.ItemDataRole
            .CheckStateRole
        ):
            return False

        check_value = getattr(
            value,
            "value",
            value,
        )

        included = (
            check_value
            == Qt.CheckState.Checked.value
        )

        return self.set_included(
            index.row(),
            included,
        )

    def flags(
        self,
        index,
    ):
        if not index.isValid():
            return (
                Qt.ItemFlag.NoItemFlags
            )

        result = (
            Qt.ItemFlag.ItemIsEnabled
            |
            Qt.ItemFlag.ItemIsSelectable
        )

        if (
            self._columns[
                index.column()
            ]
            == self.INCLUDE_COLUMN
        ):
            result |= (
                Qt.ItemFlag
                .ItemIsUserCheckable
            )

        return result

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
            if not (
                0
                <= section
                < len(
                    self._columns
                )
            ):
                return None

            column = (
                self._columns[
                    section
                ]
            )

            if (
                column
                == self.INCLUDE_COLUMN
            ):
                return "INCLUIR"

            if (
                column
                == self.SOURCE_ROW_COLUMN
            ):
                return "FILA EXCEL"

            return (
                column
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
