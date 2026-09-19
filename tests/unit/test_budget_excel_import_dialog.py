import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QPushButton, QTableView, QTabWidget

from app.config.budget_modules import OPEX_MODULE_CONFIG
from app.models.budget_excel_import import (
    BudgetExcelImportResult, BudgetImportIssue, BudgetImportIssueSeverity,
)
from app.ui.dialogs import budget_excel_import_dialog as dialog_module


pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_unvalidated_corrections_cannot_import_previous_valid_result(qapp):
    result = BudgetExcelImportResult("OPEX", "test.xlsx", "Sheet1", 1, 1, ({"ceco": "51ABC"},))
    dialog = dialog_module.BudgetExcelImportDialog(
        result=result, module_config=OPEX_MODULE_CONFIG,
        corrections={(2, "enero_usd"): "12.50"}, validation_pending=True,
    )
    try:
        assert not dialog._import_button.isEnabled()
        assert dialog.rows_to_import() == ()
        dialog.accept()
        assert dialog.result() == 0
        assert "última validación" in dialog._status_label.text()
        retry = next(button for button in dialog.findChildren(QPushButton) if button.text() == "Reintentar validación")
        retry.click()
        assert dialog.result() == dialog.REVALIDATE_CODE
        assert dialog.corrections() == {(2, "enero_usd"): "12.50"}
    finally:
        dialog.close()


@pytest.mark.parametrize("tab_index", [0, 1])
def test_corrects_selected_issue_in_its_own_tab(qapp, monkeypatch, tab_index):
    issues = (
        BudgetImportIssue(2, "enero_usd", "BAD_AMOUNT", "Monto incorrecto", BudgetImportIssueSeverity.ERROR, "error"),
        BudgetImportIssue(3, "anio_usd", "TOTAL", "Revisar total", BudgetImportIssueSeverity.WARNING, "5", expected_value="10"),
        BudgetImportIssue(4, "ceco", "CLEANED", "Dato normalizado", BudgetImportIssueSeverity.INFO),
    )
    result = BudgetExcelImportResult("OPEX", "test.xlsx", "Sheet1", 3, 1, (), issues)
    dialog = dialog_module.BudgetExcelImportDialog(result=result, module_config=OPEX_MODULE_CONFIG)
    captured = []

    def correct(*args, **kwargs):
        captured.append(args[2])
        return "12.50", True

    monkeypatch.setattr(dialog_module, "ask_text_input", correct)
    try:
        tabs = dialog.findChild(QTabWidget)
        tabs.setCurrentIndex(tab_index)
        page = tabs.widget(tab_index)
        table = page.findChild(QTableView)
        table.setCurrentIndex(table.model().index(0, 0))
        button = next(button for button in page.findChildren(QPushButton) if button.text() == "Corregir valor seleccionado")
        assert button.isEnabled()
        button.click()
        expected = issues[tab_index]
        assert dialog.corrections() == {(expected.row_number, expected.column): "12.50"}
        assert f"Fila Excel: {expected.row_number}" in captured[0]
    finally:
        dialog.close()
