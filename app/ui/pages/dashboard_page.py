from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(24)

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Resumen general del presupuesto de Tecnologia de Informacion"
        )
        subtitle.setObjectName("pageSubtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        cards_layout.addWidget(
            self._create_card(
                "Presupuesto",
                "-",
                "Presupuesto total registrado",
            )
        )

        cards_layout.addWidget(
            self._create_card(
                "Registros",
                "-",
                "Registros disponibles",
            )
        )

        cards_layout.addWidget(
            self._create_card(
                "Cambios",
                "0",
                "Cambios pendientes",
            )
        )

        layout.addLayout(cards_layout)
        layout.addStretch()

    def _create_card(
        self,
        title_text: str,
        value_text: str,
        description_text: str,
    ):
        card = QFrame()
        card.setObjectName("dashboardCard")
        card.setMinimumHeight(150)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)

        title = QLabel(title_text)
        title.setObjectName("cardTitle")

        value = QLabel(value_text)
        value.setObjectName("cardValue")

        description = QLabel(description_text)
        description.setObjectName("cardDescription")

        layout.addWidget(title)
        layout.addWidget(value)
        layout.addWidget(description)
        layout.addStretch()

        return card
