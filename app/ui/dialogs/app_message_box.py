from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


TONE_STYLES = {
    "info": {
        "background": "#ECFDF3",
        "border": "#ABEFC6",
        "title": "#067647",
    },
    "warning": {
        "background": "#FFF4E5",
        "border": "#F3D3A3",
        "title": "#92400E",
    },
    "error": {
        "background": "#FEF3F2",
        "border": "#FECDCA",
        "title": "#B42318",
    },
}


class AppMessageDialog(
    QDialog
):
    def __init__(
        self,
        *,
        title: str,
        message: str,
        tone: str = "info",
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._title = str(
            title
        )

        self._message = str(
            message
        )

        self._tone = (
            tone
            if tone in TONE_STYLES
            else "info"
        )

        self.setObjectName(
            "appMessageDialog"
        )

        self.setWindowTitle(
            self._title
        )

        self.setModal(
            True
        )

        self.setFixedWidth(
            480
        )

        self._apply_style()
        self._setup_ui()

    def _apply_style(
        self,
    ):
        tone = TONE_STYLES[
            self._tone
        ]

        self.setStyleSheet(
            f"""
            QDialog#appMessageDialog {{
                background-color: #FFFFFF;
                color: #1F2937;
            }}

            QLabel {{
                background-color: transparent;
                color: #1F2937;
            }}

            QLabel#messageTitle {{
                color: {tone["title"]};
                font-size: 19px;
                font-weight: 700;
            }}

            QFrame#messagePanel {{
                background-color:
                    {tone["background"]};
                border: 1px solid
                    {tone["border"]};
                border-radius: 8px;
            }}

            QLabel#messageText {{
                color: #344054;
                font-size: 13px;
            }}

            QPushButton#messageOkButton {{
                background-color: #2F7650;
                color: #FFFFFF;
                border: 1px solid #2F7650;
                border-radius: 6px;
                padding: 9px 24px;
                min-width: 110px;
                font-weight: 700;
            }}

            QPushButton#messageOkButton:hover {{
                background-color: #285F42;
            }}

            QPushButton#messageOkButton:pressed {{
                background-color: #204D36;
            }}
            """
        )

    def _setup_ui(
        self,
    ):
        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            28,
            24,
            28,
            24,
        )

        layout.setSpacing(
            16
        )

        title_label = QLabel(
            self._title
        )

        title_label.setObjectName(
            "messageTitle"
        )

        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title_label.setWordWrap(
            True
        )

        layout.addWidget(
            title_label
        )

        panel = QFrame()

        panel.setObjectName(
            "messagePanel"
        )

        panel_layout = QVBoxLayout(
            panel
        )

        panel_layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )

        message_label = QLabel(
            self._message
        )

        message_label.setObjectName(
            "messageText"
        )

        message_label.setWordWrap(
            True
        )

        message_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        message_label.setTextInteractionFlags(
            Qt.TextInteractionFlag
            .TextSelectableByMouse
        )

        panel_layout.addWidget(
            message_label
        )

        layout.addWidget(
            panel
        )

        button_layout = QHBoxLayout()

        button_layout.addStretch()

        ok_button = QPushButton(
            "Entendido"
        )

        ok_button.setObjectName(
            "messageOkButton"
        )

        ok_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        ok_button.clicked.connect(
            self.accept
        )

        button_layout.addWidget(
            ok_button
        )

        button_layout.addStretch()

        layout.addLayout(
            button_layout
        )


def _show_message(
    parent,
    title: str,
    message: str,
    tone: str,
):
    dialog = AppMessageDialog(
        title=title,
        message=message,
        tone=tone,
        parent=parent,
    )

    return dialog.exec()


def show_info(
    parent,
    title: str,
    message: str,
):
    return _show_message(
        parent,
        title,
        message,
        "info",
    )


def show_warning(
    parent,
    title: str,
    message: str,
):
    return _show_message(
        parent,
        title,
        message,
        "warning",
    )


def show_error(
    parent,
    title: str,
    message: str,
):
    return _show_message(
        parent,
        title,
        message,
        "error",
    )
