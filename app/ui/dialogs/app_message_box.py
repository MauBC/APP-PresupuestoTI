from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox as NativeQMessageBox,
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



class AppTextInputDialog(
    QDialog
):
    def __init__(
        self,
        *,
        title: str,
        message: str,
        initial_value: str = "",
        expected_value=None,
        confirm_text: str = "Aplicar",
        cancel_text: str = "Cancelar",
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

        self._initial_value = str(
            initial_value
            if initial_value is not None
            else ""
        )

        self._expected_value = (
            None
            if expected_value is None
            else str(
                expected_value
            )
        )

        self._confirm_text = str(
            confirm_text
        )

        self._cancel_text = str(
            cancel_text
        )

        self.setObjectName(
            "appTextInputDialog"
        )

        self.setWindowTitle(
            self._title
        )

        self.setModal(
            True
        )

        self.setFixedWidth(
            580
        )

        self._apply_style()
        self._setup_ui()

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#appTextInputDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QLabel {
                background-color: transparent;
                color: #344054;
            }

            QLabel#inputTitle {
                color: #2F7650;
                font-size: 19px;
                font-weight: 700;
            }

            QFrame#inputMessagePanel {
                background-color: #F8F9FA;
                border: 1px solid #D8DEE4;
                border-radius: 8px;
            }

            QLabel#inputMessage {
                color: #344054;
                font-size: 13px;
            }

            QFrame#expectedPanel {
                background-color: #ECFDF3;
                border: 1px solid #ABEFC6;
                border-radius: 8px;
            }

            QLabel#expectedTitle {
                color: #067647;
                font-size: 11px;
                font-weight: 700;
            }

            QLabel#expectedValue {
                color: #067647;
                font-size: 18px;
                font-weight: 700;
            }

            QLineEdit#inputValue {
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #98A2B3;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
                font-weight: 600;
                selection-background-color: #DCEFE4;
                selection-color: #1F2937;
            }

            QLineEdit#inputValue:focus {
                border: 2px solid #2F7650;
            }

            QPushButton#inputCancel {
                background-color: #FFFFFF;
                color: #344054;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 9px 18px;
                min-width: 110px;
                font-weight: 700;
            }

            QPushButton#inputCancel:hover {
                background-color: #F2F4F7;
            }

            QPushButton#inputAccept {
                background-color: #2F7650;
                color: #FFFFFF;
                border: 1px solid #2F7650;
                border-radius: 6px;
                padding: 9px 18px;
                min-width: 145px;
                font-weight: 700;
            }

            QPushButton#inputAccept:hover {
                background-color: #285F42;
            }
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
            15
        )

        title = QLabel(
            self._title
        )

        title.setObjectName(
            "inputTitle"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title.setWordWrap(
            True
        )

        layout.addWidget(
            title
        )

        message_panel = QFrame()

        message_panel.setObjectName(
            "inputMessagePanel"
        )

        message_layout = QVBoxLayout(
            message_panel
        )

        message_layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        message = QLabel(
            self._message
        )

        message.setObjectName(
            "inputMessage"
        )

        message.setWordWrap(
            True
        )

        message.setTextInteractionFlags(
            Qt.TextInteractionFlag
            .TextSelectableByMouse
        )

        message_layout.addWidget(
            message
        )

        layout.addWidget(
            message_panel
        )

        if (
            self._expected_value
            is not None
        ):
            expected_panel = QFrame()

            expected_panel.setObjectName(
                "expectedPanel"
            )

            expected_layout = QVBoxLayout(
                expected_panel
            )

            expected_layout.setContentsMargins(
                16,
                12,
                16,
                12,
            )

            expected_title = QLabel(
                "VALOR ESPERADO"
            )

            expected_title.setObjectName(
                "expectedTitle"
            )

            expected_value = QLabel(
                self._expected_value
            )

            expected_value.setObjectName(
                "expectedValue"
            )

            expected_value.setTextInteractionFlags(
                Qt.TextInteractionFlag
                .TextSelectableByMouse
            )

            expected_layout.addWidget(
                expected_title
            )

            expected_layout.addWidget(
                expected_value
            )

            layout.addWidget(
                expected_panel
            )

        value_title = QLabel(
            "Nuevo valor:"
        )

        layout.addWidget(
            value_title
        )

        self.value_input = QLineEdit()

        self.value_input.setObjectName(
            "inputValue"
        )

        self.value_input.setText(
            self._initial_value
        )

        self.value_input.selectAll()

        layout.addWidget(
            self.value_input
        )

        buttons = QHBoxLayout()

        buttons.addStretch()

        cancel_button = QPushButton(
            self._cancel_text
        )

        cancel_button.setObjectName(
            "inputCancel"
        )

        cancel_button.setCursor(
            Qt.CursorShape
            .PointingHandCursor
        )

        cancel_button.clicked.connect(
            self.reject
        )

        accept_button = QPushButton(
            self._confirm_text
        )

        accept_button.setObjectName(
            "inputAccept"
        )

        accept_button.setCursor(
            Qt.CursorShape
            .PointingHandCursor
        )

        accept_button.clicked.connect(
            self.accept
        )

        self.value_input.returnPressed.connect(
            self.accept
        )

        buttons.addWidget(
            cancel_button
        )

        buttons.addWidget(
            accept_button
        )

        layout.addLayout(
            buttons
        )

        self.value_input.setFocus()

    def value(
        self,
    ) -> str:
        return (
            self.value_input.text()
        )


class AppConfirmationDialog(
    QDialog
):
    def __init__(
        self,
        *,
        title: str,
        message: str,
        confirm_text: str = "Confirmar",
        cancel_text: str = "Cancelar",
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._title = str(title)
        self._message = str(message)

        self._confirm_text = str(
            confirm_text
        )

        self._cancel_text = str(
            cancel_text
        )

        self.setObjectName(
            "appConfirmationDialog"
        )

        self.setWindowTitle(
            self._title
        )

        self.setModal(
            True
        )

        self.setFixedWidth(
            520
        )

        self._apply_style()
        self._setup_ui()

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#appConfirmationDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QLabel {
                background-color: transparent;
                color: #344054;
            }

            QLabel#confirmationTitle {
                color: #92400E;
                font-size: 19px;
                font-weight: 700;
            }

            QFrame#confirmationPanel {
                background-color: #FFF4E5;
                border: 1px solid #F3D3A3;
                border-radius: 8px;
            }

            QLabel#confirmationText {
                color: #344054;
                font-size: 13px;
            }

            QPushButton#confirmationAccept {
                background-color: #E58B2A;
                color: #FFFFFF;
                border: 1px solid #D77A18;
                border-radius: 6px;
                padding: 9px 22px;
                min-width: 110px;
                font-weight: 700;
            }

            QPushButton#confirmationAccept:hover {
                background-color: #D77A18;
            }

            QPushButton#confirmationCancel {
                background-color: #FFFFFF;
                color: #344054;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 9px 22px;
                min-width: 110px;
                font-weight: 700;
            }

            QPushButton#confirmationCancel:hover {
                background-color: #F2F4F7;
            }
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

        title = QLabel(
            self._title
        )

        title.setObjectName(
            "confirmationTitle"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title.setWordWrap(
            True
        )

        layout.addWidget(
            title
        )

        panel = QFrame()

        panel.setObjectName(
            "confirmationPanel"
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

        message = QLabel(
            self._message
        )

        message.setObjectName(
            "confirmationText"
        )

        message.setWordWrap(
            True
        )

        message.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        panel_layout.addWidget(
            message
        )

        layout.addWidget(
            panel
        )

        buttons = QHBoxLayout()

        buttons.addStretch()

        cancel_button = QPushButton(
            self._cancel_text
        )

        cancel_button.setObjectName(
            "confirmationCancel"
        )

        cancel_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        cancel_button.clicked.connect(
            self.reject
        )

        confirm_button = QPushButton(
            self._confirm_text
        )

        confirm_button.setObjectName(
            "confirmationAccept"
        )

        confirm_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        confirm_button.clicked.connect(
            self.accept
        )

        buttons.addWidget(
            cancel_button
        )

        buttons.addWidget(
            confirm_button
        )

        buttons.addStretch()

        layout.addLayout(
            buttons
        )


def ask_text_input(
    parent,
    title: str,
    message: str,
    *,
    initial_value: str = "",
    expected_value=None,
    confirm_text: str = "Aplicar",
    cancel_text: str = "Cancelar",
):
    dialog = AppTextInputDialog(
        title=title,
        message=message,
        initial_value=initial_value,
        expected_value=expected_value,
        confirm_text=confirm_text,
        cancel_text=cancel_text,
        parent=parent,
    )

    accepted = (
        dialog.exec()
        == QDialog.DialogCode.Accepted
    )

    return (
        dialog.value(),
        accepted,
    )


def ask_confirmation(
    parent,
    title: str,
    message: str,
    *,
    confirm_text: str = "Confirmar",
    cancel_text: str = "Cancelar",
) -> bool:
    dialog = AppConfirmationDialog(
        title=title,
        message=message,
        confirm_text=confirm_text,
        cancel_text=cancel_text,
        parent=parent,
    )

    return (
        dialog.exec()
        == QDialog.DialogCode.Accepted
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



class AppMessageBox:
    """
    Adaptador compatible con las llamadas
    simples de QMessageBox usadas por la app.

    Nunca muestra el QMessageBox nativo.
    """

    StandardButton = (
        NativeQMessageBox.StandardButton
    )

    @staticmethod
    def information(
        parent,
        title,
        message,
        *_,
        **__,
    ):
        show_info(
            parent,
            str(title),
            str(message),
        )

        return (
            AppMessageBox
            .StandardButton
            .Ok
        )

    @staticmethod
    def warning(
        parent,
        title,
        message,
        *_,
        **__,
    ):
        show_warning(
            parent,
            str(title),
            str(message),
        )

        return (
            AppMessageBox
            .StandardButton
            .Ok
        )

    @staticmethod
    def critical(
        parent,
        title,
        message,
        *_,
        **__,
    ):
        show_error(
            parent,
            str(title),
            str(message),
        )

        return (
            AppMessageBox
            .StandardButton
            .Ok
        )

    @staticmethod
    def about(
        parent,
        title,
        message,
        *_,
        **__,
    ):
        show_info(
            parent,
            str(title),
            str(message),
        )

        return (
            AppMessageBox
            .StandardButton
            .Ok
        )

    @staticmethod
    def question(
        parent,
        title,
        message,
        *_,
        **__,
    ):
        confirmed = ask_confirmation(
            parent,
            str(title),
            str(message),
            confirm_text="Si",
            cancel_text="No",
        )

        if confirmed:
            return (
                AppMessageBox
                .StandardButton
                .Yes
            )

        return (
            AppMessageBox
            .StandardButton
            .No
        )
