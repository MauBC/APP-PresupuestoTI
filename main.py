import sys

from PySide6.QtGui import (
    QIcon,
)
from PySide6.QtWidgets import (
    QApplication,
)

from app.config.settings import (
    settings,
)
from app.ui.windows.main_window import (
    MainWindow,
)
from app.utils.resources import (
    resource_path,
)


APP_USER_MODEL_ID = (
    "Ransa.PresupuestoTI"
)

APP_ICON_PATH = (
    "assets/icons/app.ico"
)


def configure_windows_app_id():
    if sys.platform != "win32":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            APP_USER_MODEL_ID
        )

    except Exception:
        pass


def load_stylesheet(
    app: QApplication,
):
    style_path = resource_path(
        "assets/styles/main.qss"
    )

    if style_path.exists():
        app.setStyleSheet(
            style_path.read_text(
                encoding="utf-8-sig"
            )
        )


def load_app_icon():
    icon_path = resource_path(
        APP_ICON_PATH
    )

    if not icon_path.exists():
        return QIcon()

    return QIcon(
        str(icon_path)
    )


def main():
    configure_windows_app_id()

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        settings.APP_NAME
    )

    app.setOrganizationName(
        "Ransa"
    )

    icon = load_app_icon()

    if not icon.isNull():
        app.setWindowIcon(
            icon
        )

    load_stylesheet(
        app
    )

    window = MainWindow()

    if not icon.isNull():
        window.setWindowIcon(
            icon
        )

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()
