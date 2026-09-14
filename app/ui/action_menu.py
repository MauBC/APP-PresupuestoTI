from PySide6.QtCore import (
    QEvent,
    QObject,
)
from PySide6.QtWidgets import (
    QMenu,
    QToolButton,
)


def action_menu_source_state(
    source_button,
):
    return (
        str(
            source_button.text()
            or ""
        ).strip(),
        bool(
            source_button.isEnabled()
        ),
        str(
            source_button.toolTip()
            or ""
        ).strip(),
    )


class ActionMenuController(
    QObject
):
    def __init__(
        self,
        *,
        parent,
        sources,
        text,
        tooltip="",
    ):
        super().__init__(
            parent
        )

        self._sources = tuple(
            sources
        )

        self.button = QToolButton(
            parent
        )

        self.button.setObjectName(
            "actionMenuButton"
        )

        self.button.setText(
            text
        )

        self.button.setToolTip(
            tooltip
        )

        self.button.setPopupMode(
            QToolButton.ToolButtonPopupMode
            .InstantPopup
        )

        self.menu = QMenu(
            self.button
        )

        self.menu.setObjectName(
            "actionMenu"
        )

        self.menu.setToolTipsVisible(
            True
        )

        self.button.setMenu(
            self.menu
        )

        self._actions = []

        for source in self._sources:
            action = (
                self.menu.addAction(
                    source.text()
                )
            )

            action.triggered.connect(
                source.click
            )

            source.installEventFilter(
                self
            )

            self._actions.append(
                action
            )

        self.menu.aboutToShow.connect(
            self.sync
        )

        self.sync()

    def sync(
        self,
    ):
        any_enabled = False

        for (
            source,
            action,
        ) in zip(
            self._sources,
            self._actions,
        ):
            (
                text,
                enabled,
                tooltip,
            ) = action_menu_source_state(
                source
            )

            action.setText(
                text
            )

            action.setEnabled(
                enabled
            )

            action.setToolTip(
                tooltip
            )

            any_enabled = (
                any_enabled
                or enabled
            )

        self.button.setEnabled(
            any_enabled
        )

    def eventFilter(
        self,
        watched,
        event,
    ):
        if (
            watched in self._sources
            and event.type()
            == QEvent.Type.EnabledChange
        ):
            self.sync()

        return super().eventFilter(
            watched,
            event,
        )
