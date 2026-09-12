from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.config.budget_insert_modes import (
    BudgetInsertMode,
    get_budget_insert_options,
)


class BudgetInsertModeDialog(
    QDialog
):
    def __init__(
        self,
        *,
        module_config,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._module_config = (
            module_config
        )

        self._selected_mode = None

        self.setObjectName(
            "budgetInsertModeDialog"
        )

        self.setWindowTitle(
            "Insertar presupuesto"
        )

        self.setMinimumWidth(
            560
        )

        self._apply_style()
        self._setup_ui()

    def selected_mode(
        self,
    ):
        return self._selected_mode

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#budgetInsertModeDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QLabel#dialogTitle {
                font-size: 21px;
                font-weight: 700;
                color: #173F35;
            }

            QLabel#dialogSubtitle {
                color: #667085;
                font-size: 12px;
            }

            QFrame#insertOption {
                background-color: #F8FAF9;
                border: 1px solid #D7E5DD;
                border-radius: 9px;
            }

            QLabel#optionTitle {
                color: #173F35;
                font-size: 15px;
                font-weight: 700;
            }

            QLabel#optionDescription {
                color: #667085;
                font-size: 12px;
            }

            QPushButton#optionButton {
                background-color: #2F7650;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 700;
                min-width: 110px;
            }

            QPushButton#optionButton:hover {
                background-color: #286544;
            }

            QPushButton#optionButton:disabled {
                background-color: #D0D5DD;
                color: #667085;
            }

            QPushButton#cancelButton {
                background-color: #FFFFFF;
                color: #344054;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 8px 18px;
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
            24,
            22,
            24,
            22,
        )

        layout.setSpacing(
            14
        )

        title = QLabel(
            "Insertar presupuesto "
            + self._module_config.label
        )

        title.setObjectName(
            "dialogTitle"
        )

        subtitle = QLabel(
            "Selecciona la forma en que "
            "deseas agregar informacion "
            "al presupuesto."
        )

        subtitle.setObjectName(
            "dialogSubtitle"
        )

        subtitle.setWordWrap(
            True
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        for option in (
            get_budget_insert_options(
                self._module_config
            )
        ):
            layout.addWidget(
                self._build_option(
                    option
                )
            )

        actions = QHBoxLayout()

        actions.addStretch()

        cancel_button = QPushButton(
            "Cancelar"
        )

        cancel_button.setObjectName(
            "cancelButton"
        )

        cancel_button.clicked.connect(
            self.reject
        )

        actions.addWidget(
            cancel_button
        )

        layout.addLayout(
            actions
        )

    def _build_option(
        self,
        option,
    ):
        frame = QFrame()

        frame.setObjectName(
            "insertOption"
        )

        layout = QHBoxLayout(
            frame
        )

        layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        text_layout = QVBoxLayout()

        title = QLabel(
            option.title
        )

        title.setObjectName(
            "optionTitle"
        )

        description = QLabel(
            option.description
        )

        description.setObjectName(
            "optionDescription"
        )

        description.setWordWrap(
            True
        )

        text_layout.addWidget(
            title
        )

        text_layout.addWidget(
            description
        )

        layout.addLayout(
            text_layout,
            1,
        )

        button = QPushButton(
            (
                "Seleccionar"
                if option.enabled
                else "En preparacion"
            )
        )

        button.setObjectName(
            "optionButton"
        )

        button.setEnabled(
            option.enabled
        )

        if option.enabled:
            button.clicked.connect(
                lambda checked=False,
                mode=option.mode:
                    self._select_mode(
                        mode
                    )
            )

        layout.addWidget(
            button
        )

        return frame

    def _select_mode(
        self,
        mode: BudgetInsertMode,
    ):
        self._selected_mode = mode

        self.accept()
