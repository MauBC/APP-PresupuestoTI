from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("APP Presupuesto TI")
        self.resize(1200, 720)

        self._setup_ui()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = self._create_sidebar()
        content = self._create_content()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content, 1)

    def _create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(230)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 30, 20, 30)
        layout.setSpacing(10)

        title = QLabel("Presupuesto TI")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dashboard_button = QPushButton("Dashboard")
        presupuesto_button = QPushButton("Presupuesto")
        real_button = QPushButton("Gasto Real")
        comparacion_button = QPushButton("Comparacion")
        configuracion_button = QPushButton("Configuracion")

        layout.addWidget(title)
        layout.addSpacing(30)

        layout.addWidget(dashboard_button)
        layout.addWidget(presupuesto_button)
        layout.addWidget(real_button)
        layout.addWidget(comparacion_button)

        layout.addStretch()

        layout.addWidget(configuracion_button)

        return sidebar

    def _create_content(self):
        content = QWidget()

        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 26px; font-weight: bold;")

        subtitle = QLabel(
            "Sistema de gestion y seguimiento del presupuesto de TI."
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()

        return content