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
