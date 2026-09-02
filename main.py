import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.config.settings import settings
from app.ui.windows.main_window import MainWindow


def load_stylesheet(app: QApplication):
    style_path = (
        Path(__file__).parent
        / "assets"
        / "styles"
        / "main.qss"
    )

    if style_path.exists():
        app.setStyleSheet(
            style_path.read_text(
                encoding="utf-8-sig"
            )
        )


def main():
    app = QApplication(sys.argv)

    app.setApplicationName(settings.APP_NAME)

    load_stylesheet(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
