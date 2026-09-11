from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


REVERSAL_CONFIRMATION_TEXT = (
    "REVERTIR"
)


def is_reversal_confirmation_valid(
    value,
) -> bool:
    return (
        str(
            value
            if value is not None
            else ""
        )
        .strip()
        .upper()
        == REVERSAL_CONFIRMATION_TEXT
    )


def format_reversal_datetime(
    value,
) -> str:
    if value is None:
        return ""

    if not isinstance(
        value,
        datetime,
    ):
        return str(value)

    if (
        value.tzinfo is not None
        and value.utcoffset()
        is not None
    ):
        value = (
            value.astimezone()
        )

    return value.strftime(
        "%d/%m/%Y %H:%M:%S"
    )


def build_reversal_safety_text(
) -> str:
    return (
        "Esta operacion NO elimina el "
        "historial original y NO realiza "
        "DELETE fisico.\n\n"
        "- Si el batch modifico filas "
        "existentes, se intentaran restaurar "
        "sus valores anteriores.\n"
        "- Si el batch creo filas nuevas, "
        "esas filas se conservaran y se "
        "DESHABILITARAN mediante baja logica.\n"
        "- Si alguna fila fue modificada "
        "despues, la reversion se bloqueara "
        "por concurrencia."
    )


def build_reversal_summary(
    batch,
) -> str:
    return (
        f"<b>Batch:</b> "
        f"{batch.batch_id}<br>"
        f"<b>Fecha:</b> "
        f"{format_reversal_datetime(batch.created_at)}"
        f"<br>"
        f"<b>Usuario original:</b> "
        f"{batch.actor}<br>"
        f"<b>Modulo:</b> "
        f"{batch.budget_module}<br>"
        f"<b>Filas afectadas:</b> "
        f"{batch.row_count:,}<br>"
        f"<b>Cambios registrados:</b> "
        f"{batch.field_count:,}"
    )


def build_reversal_applied_impact(
    detail,
    result,
) -> str:
    changes = tuple(
        getattr(
            detail,
            "changes",
            (),
        )
        or ()
    )

    inserted_row_ids = {
        str(
            getattr(
                change,
                "row_id",
                "",
            )
            or ""
        ).strip()
        for change in changes
        if (
            getattr(
                change,
                "version_before",
                None,
            )
            == 0
        )
        and str(
            getattr(
                change,
                "row_id",
                "",
            )
            or ""
        ).strip()
    }

    disabled_count = len(
        inserted_row_ids
    )

    total_rows = int(
        getattr(
            result,
            "row_count",
            0,
        )
        or 0
    )

    restored_count = max(
        total_rows
        - disabled_count,
        0,
    )

    field_count = int(
        getattr(
            result,
            "field_count",
            0,
        )
        or 0
    )

    lines = [
        f"Filas procesadas: "
        f"{total_rows:,}",
    ]

    if restored_count:
        lines.append(
            "Filas con valores "
            "restaurados: "
            f"{restored_count:,}"
        )

    if disabled_count:
        lines.append(
            "Filas nuevas "
            "deshabilitadas: "
            f"{disabled_count:,}"
        )

    lines.append(
        "Cambios compensatorios: "
        f"{field_count:,}"
    )

    if disabled_count:
        lines.append("")
        lines.append(
            "Las filas nuevas NO fueron "
            "eliminadas fisicamente; "
            "quedaron deshabilitadas."
        )

    return "\n".join(
        lines
    )


class ReversalConfirmDialog(
    QDialog
):
    def __init__(
        self,
        batch,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._batch = batch

        self.setObjectName(
            "reversalConfirmDialog"
        )

        self.setWindowTitle(
            "Confirmar reversión"
        )

        self.setModal(
            True
        )

        self.setMinimumWidth(
            650
        )

        self._apply_style()
        self._setup_ui()

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#reversalConfirmDialog {
                background-color: #FFFFFF;
                color: #1F2933;
            }

            QDialog#reversalConfirmDialog QLabel {
                background-color: transparent;
                color: #1F2933;
            }

            QLabel#reversalTitle {
                color: #164D36;
                font-size: 21px;
                font-weight: 700;
            }

            QLabel#reversalWarning {
                background-color: #FFF7ED;
                color: #9A3412;
                border: 1px solid #FED7AA;
                border-radius: 7px;
                padding: 12px 14px;
                font-weight: 600;
            }

            QLabel#reversalSummary {
                background-color: #F7FAF8;
                color: #344054;
                border: 1px solid #D7E2DB;
                border-radius: 7px;
                padding: 12px 14px;
            }

            QLabel#reversalHelp {
                color: #475467;
            }

            QLineEdit {
                background-color: #FFFFFF;
                color: #1F2933;
                border: 1px solid #B8C9BF;
                border-radius: 6px;
                padding: 9px 10px;
            }

            QLineEdit:focus {
                border: 2px solid #2F7650;
            }

            QPushButton {
                min-width: 110px;
                padding: 9px 18px;
                border-radius: 6px;
                font-weight: 600;
            }

            QPushButton#cancelReversalButton {
                background-color: #FFFFFF;
                color: #344054;
                border: 1px solid #B8C9BF;
            }

            QPushButton#confirmReversalButton {
                background-color: #C2410C;
                color: #FFFFFF;
                border: 1px solid #C2410C;
            }

            QPushButton#confirmReversalButton:hover {
                background-color: #9A3412;
            }

            QPushButton#confirmReversalButton:disabled {
                background-color: #D0D5DD;
                color: #667085;
                border-color: #D0D5DD;
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
            26,
            24,
            26,
            24,
        )

        layout.setSpacing(
            14
        )

        title = QLabel(
            "Revertir cambios aplicados"
        )

        title.setObjectName(
            "reversalTitle"
        )

        layout.addWidget(
            title
        )

        warning = QLabel(
            build_reversal_safety_text()
        )

        warning.setObjectName(
            "reversalWarning"
        )

        warning.setWordWrap(
            True
        )

        layout.addWidget(
            warning
        )

        summary = QLabel(
            build_reversal_summary(
                self._batch
            )
        )

        summary.setObjectName(
            "reversalSummary"
        )

        summary.setWordWrap(
            True
        )

        summary.setTextInteractionFlags(
            Qt.TextInteractionFlag
            .TextSelectableByMouse
        )

        layout.addWidget(
            summary
        )

        help_label = QLabel(
            "La operacion es compensatoria: "
            "el batch original permanece en "
            "el historial y se crea un nuevo "
            "batch auditado.\n\n"
            "Si existe un conflicto de version, "
            "la reversion se bloqueara y los "
            "datos vigentes no seran reemplazados."
            "\n\n"
            "Para continuar escribe "
            "<b>REVERTIR</b>:"
        )

        help_label.setObjectName(
            "reversalHelp"
        )

        help_label.setWordWrap(
            True
        )

        layout.addWidget(
            help_label
        )

        self.confirmation_input = (
            QLineEdit()
        )

        self.confirmation_input.setPlaceholderText(
            "Escribe REVERTIR"
        )

        layout.addWidget(
            self.confirmation_input
        )

        buttons = QHBoxLayout()

        buttons.addStretch()

        self.cancel_button = QPushButton(
            "Cancelar"
        )

        self.cancel_button.setObjectName(
            "cancelReversalButton"
        )

        self.confirm_button = QPushButton(
            "Revertir"
        )

        self.confirm_button.setObjectName(
            "confirmReversalButton"
        )

        self.confirm_button.setEnabled(
            False
        )

        buttons.addWidget(
            self.cancel_button
        )

        buttons.addWidget(
            self.confirm_button
        )

        layout.addLayout(
            buttons
        )

        self.confirmation_input.textChanged.connect(
            self._update_confirmation
        )

        self.cancel_button.clicked.connect(
            self.reject
        )

        self.confirm_button.clicked.connect(
            self.accept
        )

    def _summary_text(
        self,
    ) -> str:
        return build_reversal_summary(
            self._batch
        )

    def _update_confirmation(
        self,
        value,
    ):
        self.confirm_button.setEnabled(
            is_reversal_confirmation_valid(
                value
            )
        )
