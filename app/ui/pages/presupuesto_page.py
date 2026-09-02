from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)


class PresupuestoPage(QWidget):
    def __init__(self):
        super().__init__()

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(18)

        title = QLabel("Presupuesto")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Consulta y mantenimiento de los registros presupuestales"
        )
        subtitle.setObjectName("pageSubtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Buscar en los registros..."
        )

        self.refresh_button = QPushButton("Actualizar")
        self.save_button = QPushButton("Guardar cambios")

        self.save_button.setObjectName("primaryButton")
        self.save_button.setEnabled(False)

        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(self.refresh_button)
        toolbar.addWidget(self.save_button)

        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)

        self.table.setColumnCount(4)

        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Descripcion",
                "Importe",
                "Estado",
            ]
        )

        layout.addWidget(self.table, 1)

        self.status_label = QLabel(
            "Esperando conexion con Google Cloud"
        )
        self.status_label.setObjectName("tableStatus")

        layout.addWidget(self.status_label)
