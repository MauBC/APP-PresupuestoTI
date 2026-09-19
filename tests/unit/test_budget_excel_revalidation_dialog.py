import os
from threading import Event
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog

from app.ui.dialogs.budget_excel_revalidation_dialog import BudgetExcelRevalidationDialog
from app.ui.workers import budget_excel_import as worker_module


pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def dialog():
    return BudgetExcelRevalidationDialog(
        module_config=object(), source_path="test.xlsx", actor="tester",
        corrections={(2, "enero_usd"): "12.50"},
    )


def test_revalidation_keeps_event_loop_active_and_passes_corrections(qapp, monkeypatch):
    release = Event()
    received = []
    expected = object()

    def prepare(path, **kwargs):
        received.append(kwargs)
        assert release.wait(3), "La GUI no proceso el temporizador durante la validacion"
        return expected

    monkeypatch.setattr(worker_module, "BudgetExcelImportService", lambda config: SimpleNamespace(prepare=prepare))
    progress = dialog()
    timer = QTimer(progress)
    timer.setSingleShot(True)
    timer.timeout.connect(release.set)
    timer.start(20)
    assert progress.exec() == QDialog.DialogCode.Accepted
    assert progress.prepared_result is expected
    assert received[0]["overrides"] == {(2, "enero_usd"): "12.50"}
    assert not progress._worker.isRunning()


def test_revalidation_failure_returns_error_without_old_result(qapp, monkeypatch):
    def prepare(*args, **kwargs):
        raise ValueError("Archivo no disponible")

    monkeypatch.setattr(worker_module, "BudgetExcelImportService", lambda config: SimpleNamespace(prepare=prepare))
    progress = dialog()
    assert progress.exec() == QDialog.DialogCode.Rejected
    assert progress.prepared_result is None
    assert "Archivo no disponible" in progress.error_message
    assert not progress._worker.isRunning()


def test_cancel_waits_for_worker_and_discards_result(qapp, monkeypatch):
    release = Event()

    def prepare(*args, **kwargs):
        release.wait(3)
        return object()

    monkeypatch.setattr(worker_module, "BudgetExcelImportService", lambda config: SimpleNamespace(prepare=prepare))
    progress = dialog()

    def cancel():
        progress.reject()
        release.set()

    QTimer.singleShot(20, cancel)
    assert progress.exec() == QDialog.DialogCode.Rejected
    assert progress.prepared_result is None
    assert progress.error_message is None
    assert not progress._worker.isRunning()
