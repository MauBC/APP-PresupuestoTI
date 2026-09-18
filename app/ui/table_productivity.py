from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
)


TABLE_SHORTCUT_SEQUENCES = (
    "Ctrl+F",
    "Ctrl+R",
    "Ctrl+Z",
    "Esc",
)


def focus_table_search(
    search_input,
):
    search_input.setFocus(
        Qt.FocusReason.ShortcutFocusReason
    )

    search_input.selectAll()


def clear_table_search(
    *,
    search_input,
    table,
):
    if search_input.text():
        search_input.clear()

    table.setFocus(
        Qt.FocusReason.ShortcutFocusReason
    )


def install_table_productivity_shortcuts(
    owner,
    *,
    search_input,
    table,
    refresh_callback,
    undo_callback,
):
    shortcuts = []

    find_shortcut = QShortcut(
        QKeySequence("Ctrl+F"),
        owner,
    )

    find_shortcut.setContext(
        Qt.ShortcutContext
        .WidgetWithChildrenShortcut
    )

    find_shortcut.activated.connect(
        lambda:
            focus_table_search(
                search_input
            )
    )

    shortcuts.append(
        find_shortcut
    )

    refresh_shortcut = QShortcut(
        QKeySequence("Ctrl+R"),
        table,
    )

    refresh_shortcut.setContext(
        Qt.ShortcutContext.WidgetShortcut
    )

    refresh_shortcut.activated.connect(
        refresh_callback
    )

    shortcuts.append(
        refresh_shortcut
    )

    undo_shortcut = QShortcut(
        QKeySequence("Ctrl+Z"),
        table,
    )

    undo_shortcut.setContext(
        Qt.ShortcutContext.WidgetShortcut
    )

    undo_shortcut.activated.connect(
        undo_callback
    )

    shortcuts.append(
        undo_shortcut
    )

    for widget in (
        search_input,
        table,
    ):
        escape_shortcut = QShortcut(
            QKeySequence("Esc"),
            widget,
        )

        escape_shortcut.setContext(
            Qt.ShortcutContext.WidgetShortcut
        )

        escape_shortcut.activated.connect(
            lambda:
                clear_table_search(
                    search_input=search_input,
                    table=table,
                )
        )

        shortcuts.append(
            escape_shortcut
        )

    return tuple(
        shortcuts
    )



def capture_table_layout(
    *,
    table,
    columns,
):
    columns = tuple(
        columns
        or ()
    )

    widths = []

    for index, column in enumerate(
        columns
    ):
        if table.isColumnHidden(
            index
        ):
            continue

        width = int(
            table.columnWidth(
                index
            )
        )

        if width > 0:
            widths.append(
                (
                    str(column),
                    width,
                )
            )

    header = (
        table.horizontalHeader()
    )

    section = int(
        header.sortIndicatorSection()
    )

    sort_column = None

    if (
        0
        <= section
        < len(columns)
    ):
        sort_column = (
            columns[section]
        )

    sort_order = (
        "desc"
        if (
            header.sortIndicatorOrder()
            == Qt.SortOrder
            .DescendingOrder
        )
        else "asc"
    )

    return (
        tuple(widths),
        sort_column,
        sort_order,
    )


def merge_column_widths(
    previous,
    current,
):
    result = {}

    for source in (
        previous or (),
        current or (),
    ):
        for column, width in source:
            column = str(
                column
            ).strip()

            try:
                width = int(
                    width
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

            if (
                column
                and width > 0
            ):
                result[
                    column
                ] = width

    return tuple(
        result.items()
    )


def restore_table_layout(
    *,
    table,
    columns,
    column_widths=(),
    sort_column=None,
    sort_order="asc",
):
    columns = tuple(
        columns
        or ()
    )

    width_map = {
        str(column):
            int(width)
        for column, width
        in (
            column_widths
            or ()
        )
        if (
            str(column).strip()
            and int(width) > 0
        )
    }

    for index, column in enumerate(
        columns
    ):
        width = width_map.get(
            str(column)
        )

        if width is None:
            continue

        table.setColumnWidth(
            index,
            width,
        )

    if (
        sort_column
        and sort_column in columns
    ):
        column_index = (
            columns.index(
                sort_column
            )
        )

        order = (
            Qt.SortOrder
            .DescendingOrder
            if str(
                sort_order
            ).lower()
            == "desc"
            else Qt.SortOrder
            .AscendingOrder
        )

        table.sortByColumn(
            column_index,
            order,
        )
