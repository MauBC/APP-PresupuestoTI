from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QPushButton, QVBoxLayout

from app.ui.workers.budget_excel_import import BudgetExcelImportThread


class BudgetExcelRevalidationDialog(QDialog):
    """Mantiene la interfaz activa mientras se revalidan correcciones locales."""

    def __init__(self, *, module_config, source_path, actor, corrections, parent=None):
        super().__init__(parent)
        self.prepared_result = None
        self.error_message = None
        self._cancel_requested = False
        self._finished = False
        self.setWindowTitle("Revalidando Excel")
        self.setFixedWidth(460)
        self.setStyleSheet("QDialog { background: white; color: #344054; }"
                           "QLabel { color: #344054; }"
                           "QPushButton { padding: 8px 18px; color: #344054; "
                           "background: #F2F4F7; border: 1px solid #D0D5DD; border-radius: 6px; }"
                           "QPushButton:disabled { color: #98A2B3; }"
                           "QProgressBar { border: 1px solid #D7E5DD; border-radius: 4px; "
                           "background: #F2F4F7; min-height: 12px; }"
                           "QProgressBar::chunk { background: #2F7650; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        self.status_label = QLabel("Validando las correcciones. El archivo original no se modifica.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        progress = QProgressBar()
        progress.setRange(0, 0)
        layout.addWidget(progress)
        self.cancel_button = QPushButton("Cancelar revisión")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        self._worker = BudgetExcelImportThread(
            module_config=module_config, file_path=source_path, actor=actor,
            overrides=corrections, parent=self,
        )
        self._worker.loaded.connect(self._loaded)
        self._worker.failed.connect(self._failed)
        self._worker.finished.connect(self._complete)
        self.ensurePolished()
        self.resize(self.width(), layout.totalHeightForWidth(self.width()))

    def exec(self):
        QTimer.singleShot(0, self._worker.start)
        return super().exec()

    def _loaded(self, result):
        if not self._cancel_requested:
            self.prepared_result = result

    def _failed(self, message):
        if not self._cancel_requested:
            self.error_message = message

    def _complete(self):
        self._finished = True
        if self._cancel_requested:
            self.prepared_result = None
            self.error_message = None
        if self.prepared_result is not None:
            super().accept()
        else:
            super().reject()

    def reject(self):
        if self._finished:
            super().reject()
            return
        self._cancel_requested = True
        self._worker.requestInterruption()
        self.cancel_button.setEnabled(False)
        self.status_label.setText(
            "Cancelando revisión. Esperando a que termine la lectura en curso; "
            "las correcciones se conservarán para reintentar."
        )
        self.resize(self.width(), self.layout().totalHeightForWidth(self.width()))

    def closeEvent(self, event):
        if not self._finished:
            self.reject()
            event.ignore()
        else:
            super().closeEvent(event)
