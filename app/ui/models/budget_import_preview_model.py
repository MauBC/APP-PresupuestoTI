
from decimal import Decimal

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
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
        excluded_source_rows=(),
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

        # Los row_id se regeneran al preparar el Excel. La fila de origen
        # conserva la identidad aunque cambie el orden o una fila sea invalida.
        self._excluded_source_rows = set(excluded_source_rows)
        self._included = [number not in self._excluded_source_rows for number in numbers]
        self._included_count = sum(self._included)

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
        return self._included_count

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

    def excluded_source_rows(self):
        return frozenset(self._excluded_source_rows)

    def set_included(
        self,
        row_index,
        included,
    ) -> bool:
        return self.set_rows_included((row_index,), included)

    def set_rows_included(self, row_indices, included) -> bool:
        """Update a selection once, without a recount or signal per row."""
        value = bool(included)
        first = len(self._rows)
        last = -1
        for row_index in row_indices:
            if not 0 <= row_index < len(self._rows):
                continue
            if self._included[row_index] == value:
                continue
            self._included[row_index] = value
            self._included_count += 1 if value else -1
            source_row = self._source_row_numbers[row_index]
            if value:
                self._excluded_source_rows.discard(source_row)
            else:
                self._excluded_source_rows.add(source_row)
            first = min(first, row_index)
            last = max(last, row_index)

        if last < 0:
            return False
        self.dataChanged.emit(
            self.index(first, 0), self.index(last, 0),
            [Qt.ItemDataRole.CheckStateRole],
        )
        return True

    def include_all(self):
        self._excluded_source_rows.clear()
        self.set_rows_included(range(len(self._rows)), True)

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
            "context",
            "CONTEXTO",
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
        (
            "expected_value",
            "ESPERADO",
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

    def issue_at(
        self,
        row_index,
    ):
        if not (
            0
            <= row_index
            < len(
                self._issues
            )
        ):
            return None

        return self._issues[
            row_index
        ]

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
            return format_import_value(
                value
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

class BudgetImportIssueFilterProxyModel(
    QSortFilterProxyModel
):
    def __init__(
        self,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._search_text = ""
        self._severity = None

    def set_search_text(
        self,
        value,
    ):
        self._search_text = str(
            value
            if value is not None
            else ""
        ).strip().casefold()

        self.invalidate()

    def set_severity(
        self,
        value,
    ):
        if value is None:
            self._severity = None

        else:
            raw = getattr(
                value,
                "value",
                value,
            )

            self._severity = str(
                raw
            ).strip().upper() or None

        self.invalidate()

    def filterAcceptsRow(
        self,
        source_row,
        source_parent,
    ):
        source = self.sourceModel()

        if source is None:
            return False

        issue = source.issue_at(
            source_row
        )

        if issue is None:
            return False

        severity = getattr(
            issue.severity,
            "value",
            issue.severity,
        )

        if (
            self._severity
            and str(
                severity
            ).strip().upper()
            != self._severity
        ):
            return False

        if not self._search_text:
            return True

        values = (
            issue.row_number,
            issue.context,
            severity,
            issue.code,
            issue.column,
            issue.message,
            issue.raw_value,
            issue.expected_value,
        )

        haystack = " ".join(
            ""
            if value is None
            else str(value)
            for value
            in values
        ).casefold()

        return (
            self._search_text
            in haystack
        )
