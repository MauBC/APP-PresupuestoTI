from decimal import (
    Decimal,
    InvalidOperation,
)

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
)
from app.models.page_result import (
    PageResult,
)
from app.services.presupuesto_workspace import (
    SESSION_ROW_ID,
)


class PresupuestoTableModel(
    QAbstractTableModel
):
    workspace_changed = Signal()
    edit_failed = Signal(str)

    USD_BACKGROUND = QColor(
        "#EEF8F1"
    )

    MODIFIED_BACKGROUND = QColor(
        "#FFF1C7"
    )

    NEW_ROW_BACKGROUND = QColor(
        "#EAF7EE"
    )

    DISABLED_BACKGROUND = QColor(
        "#F0F2F1"
    )

    DISABLED_FOREGROUND = QColor(
        "#8A948E"
    )

    def __init__(
        self,
        workspace,
        parent=None,
    ):
        super().__init__(parent)

        self._workspace = workspace
        self._config = (
            workspace.module_config
        )

        self._rows = []
        self._columns = ()

        self._original_rows = {}
        self._new_row_ids = set()

        self._amount_columns = set(
            self._config.amount_columns
        )

        self._month_columns = set(
            self._config.month_columns
        )

        self._annual_column = (
            self._config.annual_column
        )

    def set_page(
        self,
        page: PageResult,
    ):
        self.beginResetModel()

        self._rows = [
            dict(row)
            for row in page.rows
        ]

        self._columns = tuple(
            page.columns
        )

        self._original_rows = {}
        self._new_row_ids = set()

        for row in self._rows:
            row_id = row.get(
                SESSION_ROW_ID
            )

            if row_id is None:
                continue

            self._original_rows[row_id] = (
                self._workspace
                .get_original_row(
                    row_id
                )
            )

            if (
                self._workspace
                .is_new_row(
                    row_id
                )
            ):
                self._new_row_ids.add(
                    row_id
                )

        self.endResetModel()

    def clear(self):
        self.beginResetModel()

        self._rows = []
        self._columns = ()
        self._original_rows = {}
        self._new_row_ids = set()

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

        enabled = bool(
            row.get(
                HABILITADO_COLUMN,
                True,
            )
        )

        if role == Qt.ItemDataRole.DisplayRole:
            if column == HABILITADO_COLUMN:
                return (
                    "Si"
                    if enabled
                    else "No"
                )

            if value is None:
                return ""

            if isinstance(value, Decimal):
                return f"{value:,.2f}"

            return str(value)

        if role == Qt.ItemDataRole.EditRole:
            if column in self._amount_columns:
                if value is None:
                    return ""

                return str(value)

            return value

        if (
            role
            == Qt.ItemDataRole.CheckStateRole
            and column == HABILITADO_COLUMN
        ):
            return (
                Qt.CheckState.Checked
                if enabled
                else Qt.CheckState.Unchecked
            )

        if role == Qt.ItemDataRole.UserRole:
            return value

        if role == Qt.ItemDataRole.BackgroundRole:
            row_id = row.get(
                SESSION_ROW_ID
            )

            if row_id in self._new_row_ids:
                return (
                    self.NEW_ROW_BACKGROUND
                )

            if self._is_modified(
                row,
                column,
            ):
                return (
                    self.MODIFIED_BACKGROUND
                )

            if not enabled:
                return (
                    self.DISABLED_BACKGROUND
                )

            if column in self._amount_columns:
                return self.USD_BACKGROUND

        if (
            role
            == Qt.ItemDataRole.ForegroundRole
            and not enabled
        ):
            return (
                self.DISABLED_FOREGROUND
            )

        if (
            role
            == Qt.ItemDataRole.TextAlignmentRole
            and column in self._amount_columns
        ):
            return (
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

        if role == Qt.ItemDataRole.ToolTipRole:
            if column == HABILITADO_COLUMN:
                return (
                    "Desmarcar excluye el gasto de "
                    "Dashboard y Agrupaciones sin "
                    "eliminar sus importes."
                )

            if column in self._month_columns:
                return (
                    "Doble clic para modificar "
                    "el importe mensual en USD."
                )

            if column == self._annual_column:
                return (
                    "Doble clic para modificar el "
                    "total anual. Los meses se "
                    "redistribuiran proporcionalmente."
                )

        return None

    def flags(
        self,
        index,
    ):
        if not index.isValid():
            return (
                Qt.ItemFlag.NoItemFlags
            )

        column = self._columns[
            index.column()
        ]

        flags = (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )

        if column == HABILITADO_COLUMN:
            flags |= (
                Qt.ItemFlag.ItemIsUserCheckable
            )

        if column in self._amount_columns:
            flags |= (
                Qt.ItemFlag.ItemIsEditable
            )

        return flags

    def setData(
        self,
        index,
        value,
        role=Qt.ItemDataRole.EditRole,
    ):
        if not index.isValid():
            return False

        row = self._rows[
            index.row()
        ]

        column = self._columns[
            index.column()
        ]

        row_id = row.get(
            SESSION_ROW_ID
        )

        if row_id is None:
            self.edit_failed.emit(
                "La fila no contiene un "
                "identificador de sesion."
            )

            return False

        try:
            changed = False

            if (
                column == HABILITADO_COLUMN
                and
                role
                == Qt.ItemDataRole.CheckStateRole
            ):
                enabled = value in (
                    Qt.CheckState.Checked,
                    Qt.CheckState.Checked.value,
                    True,
                )

                changed = (
                    self._workspace
                    .set_enabled(
                        row_id,
                        enabled,
                    )
                )

            elif (
                column in self._amount_columns
                and
                role
                in (
                    Qt.ItemDataRole.EditRole,
                    Qt.ItemDataRole.DisplayRole,
                )
            ):
                amount = (
                    self._parse_decimal(
                        value
                    )
                )

                if column == self._annual_column:
                    changed = (
                        self._workspace
                        .edit_annual(
                            row_id,
                            amount,
                        )
                    )

                else:
                    changed = (
                        self._workspace
                        .edit_month(
                            row_id,
                            column,
                            amount,
                        )
                    )

            else:
                return False

            if not changed:
                return False

            self._rows[
                index.row()
            ] = (
                self._workspace
                .get_row(
                    row_id
                )
            )

            first = self.index(
                index.row(),
                0,
            )

            last = self.index(
                index.row(),
                self.columnCount() - 1,
            )

            self.dataChanged.emit(
                first,
                last,
                [
                    Qt.ItemDataRole.DisplayRole,
                    Qt.ItemDataRole.EditRole,
                    Qt.ItemDataRole.UserRole,
                    Qt.ItemDataRole.BackgroundRole,
                    Qt.ItemDataRole.ForegroundRole,
                    Qt.ItemDataRole.CheckStateRole,
                ],
            )

            self.workspace_changed.emit()

            return True

        except (
            ValueError,
            InvalidOperation,
        ) as exc:
            self.edit_failed.emit(
                str(exc)
            )

            return False

        except Exception as exc:
            self.edit_failed.emit(
                f"{type(exc).__name__}: {exc}"
            )

            return False

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

    def session_row_id(
        self,
        row_index: int,
    ):
        if (
            row_index < 0
            or
            row_index >= len(self._rows)
        ):
            return None

        return self._rows[
            row_index
        ].get(
            SESSION_ROW_ID
        )

    def _is_modified(
        self,
        row,
        column,
    ) -> bool:
        row_id = row.get(
            SESSION_ROW_ID
        )

        if row_id is None:
            return False

        original = (
            self._original_rows.get(
                row_id
            )
        )

        if original is None:
            return False

        return (
            row.get(column)
            != original.get(column)
        )

    @staticmethod
    def _parse_decimal(
        value,
    ) -> Decimal:
        if isinstance(value, Decimal):
            return value

        text = str(value).strip()

        text = (
            text
            .replace("US$", "")
            .replace("$", "")
            .replace(" ", "")
            .replace(",", "")
        )

        if not text:
            raise ValueError(
                "El importe no puede estar vacio."
            )

        try:
            return Decimal(text)

        except InvalidOperation as exc:
            raise ValueError(
                f"Importe no valido: {value}"
            ) from exc
