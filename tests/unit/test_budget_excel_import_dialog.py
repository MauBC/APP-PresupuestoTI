import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QPushButton, QTableView, QTabWidget
from PySide6.QtCore import Qt

from app.config.budget_modules import OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG
from app.models.budget_excel_import import (
    BudgetExcelImportResult, BudgetImportIssue, BudgetImportIssueSeverity,
)
from app.ui.dialogs import budget_excel_import_dialog as dialog_module


pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("config", [OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG])
def test_filtered_exclusion_is_restored_after_revalidation(qapp, config):
    ceco_column = "ceco" if config.module.value == "OPEX" else "codigo_ceco"
    result = BudgetExcelImportResult(
        config.module.value, "test.xlsx", "Sheet1", 2, 1,
        ({ceco_column: "51AAA"}, {ceco_column: "51BBB"}), source_row_numbers=(9, 12),
    )
    dialog = dialog_module.BudgetExcelImportDialog(result=result, module_config=config)
    try:
        proxy = dialog._preview_proxy
        proxy.setFilterFixedString("51BBB")
        proxy.sort(1, Qt.SortOrder.DescendingOrder)
        dialog._preview_table.selectRow(0)
        dialog._exclude_selected_preview_rows()
        assert dialog.excluded_source_rows() == frozenset({12})
        exclusions = dialog.excluded_source_rows()
    finally:
        dialog.close()
    reopened = dialog_module.BudgetExcelImportDialog(
        result=result, module_config=config, excluded_source_rows=exclusions,
    )
    try:
        assert reopened.rows_to_import() == (result.rows[0],)
        assert "Incluidas: 1 | Excluidas: 1" in reopened._preview_selection_label.text()
        reopened._preview_model.set_included(0, False)
        assert not reopened._import_button.isEnabled()
        reopened._include_all_preview_rows()
        assert reopened.excluded_source_rows() == frozenset()
        assert reopened._import_button.isEnabled()
        assert reopened.rows_to_import() == result.rows
    finally:
        reopened.close()


def test_exclusions_survive_a_result_without_preview_rows(qapp):
    result = BudgetExcelImportResult("OPEX", "test.xlsx", "Sheet1", 1, 1, ())
    dialog = dialog_module.BudgetExcelImportDialog(
        result=result, module_config=OPEX_MODULE_CONFIG, excluded_source_rows=(9,),
    )
    try:
        assert dialog.excluded_source_rows() == frozenset({9})
        assert dialog.rows_to_import() == ()
    finally:
        dialog.close()


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


@pytest.mark.parametrize("config", [OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG])
def test_bulk_exclusion_maps_filtered_sorted_selection_once(qapp, config):
    ceco = "ceco" if config == OPEX_MODULE_CONFIG else "codigo_ceco"
    rows = tuple({ceco: "51KEEP" if i % 2 else "51DROP"} for i in range(100))
    result = BudgetExcelImportResult(config.module.value, "test.xlsx", "Sheet1", 100, 1, rows)
    dialog = dialog_module.BudgetExcelImportDialog(result=result, module_config=config)
    try:
        proxy = dialog._preview_proxy
        proxy.setFilterFixedString("51DROP")
        proxy.sort(1, Qt.SortOrder.DescendingOrder)
        dialog._preview_table.selectAll()
        changes = []
        dialog._preview_model.dataChanged.connect(lambda *_: changes.append(True))
        dialog._exclude_selected_preview_rows()
        assert len(changes) == 1
        assert dialog.excluded_source_rows() == frozenset(range(2, 102, 2))
        assert dialog.rows_to_import() == tuple(row for row in rows if row[ceco] == "51KEEP")
        assert "Incluidas: 50 | Excluidas: 50" in dialog._preview_selection_label.text()
        proxy.setFilterFixedString("")
        dialog._preview_table.selectAll()
        dialog._exclude_selected_preview_rows()
        assert len(changes) == 2
        assert not dialog._import_button.isEnabled()
        dialog._include_all_preview_rows()
        assert len(changes) == 3
        assert dialog._import_button.isEnabled()
        assert dialog.rows_to_import() == rows
    finally:
        dialog.close()
