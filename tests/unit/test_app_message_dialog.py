import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from app.ui.dialogs.app_message_box import AppMessageDialog


pytestmark = pytest.mark.unit


def test_wrapped_diagnostic_fits_in_fixed_width_message_dialog():
    app = QApplication.instance() or QApplication([])
    message = "\n".join([
        "Fila Excel 8 | CECO 60BK000004 | RECOVERABLE_NOT_FOUND: "
        "No existe un prefijo de RECUPERABLES.xlsx para el CECO 60BK000004."
    ] * 5 + ["Hay 1 incidencia adicional. Corrige los datos y vuelve a analizar."])
    dialog = AppMessageDialog(title="No se pudo preparar la importacion", message=message)
    try:
        # Renderizar aplica la geometria real sin abrir una ventana interactiva.
        dialog.grab()
        app.processEvents()
        label = dialog.findChild(QLabel, "messageText")
        assert label.height() >= label.heightForWidth(label.width())
        assert dialog.width() == 480
    finally:
        dialog.close()
