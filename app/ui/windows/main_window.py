from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import settings
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.presupuesto_page import PresupuestoPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(settings.APP_NAME)
        self.resize(
            settings.WINDOW_WIDTH,
            settings.WINDOW_HEIGHT,
        )

        self._setup_ui()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = self._create_sidebar()

        self.pages = QStackedWidget()

        self.dashboard_page = DashboardPage()
        self.presupuesto_page = PresupuestoPage()

        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.presupuesto_page)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages, 1)

    def _create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(settings.SIDEBAR_WIDTH)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 26, 18, 24)
        layout.setSpacing(8)

        title = QLabel("Presupuesto TI")
        title.setObjectName("appTitle")

        subtitle = QLabel("Gestion presupuestal")
        subtitle.setObjectName("appSubtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(26)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        dashboard_button = self._create_nav_button(
            "Dashboard",
            0,
        )

        presupuesto_button = self._create_nav_button(
            "Presupuesto",
            1,
        )

        layout.addWidget(dashboard_button)
        layout.addWidget(presupuesto_button)

        layout.addStretch()

        version_label = QLabel(
            f"Version {settings.APP_VERSION}"
        )
        version_label.setObjectName("appSubtitle")

        layout.addWidget(version_label)

        dashboard_button.setChecked(True)

        return sidebar

    def _create_nav_button(
        self,
        text: str,
        page_index: int,
    ):
        button = QPushButton(text)

        button.setObjectName("sidebarButton")
        button.setCheckable(True)
        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button.clicked.connect(
            lambda checked=False, index=page_index:
            self.pages.setCurrentIndex(index)
        )

        self.button_group.addButton(button)

        return button
