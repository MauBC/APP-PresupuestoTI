from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.config.budget_modules import OPEX_MODULE_CONFIG
from app.models.budget_excel_import import BudgetExcelImportResult
from app.ui.pages import presupuesto_page as page_module


pytestmark = pytest.mark.unit


@pytest.mark.parametrize("error", ["Archivo temporalmente bloqueado", None])
def test_failed_or_cancelled_revalidation_requires_retry_before_import(monkeypatch, error):
    original = BudgetExcelImportResult("OPEX", "test.xlsx", "Sheet1", 1, 1, ({"value": "original"},))
    corrected = replace(original, rows=({"value": "corregido"},))
    pending_states, imported, correction_requests = [], [], []
    dialog_codes = iter([1001, 1001, 1])
    outcomes = iter([(None, error), (corrected, None)])

    class ReviewDialog:
        REVALIDATE_CODE = 1001

        def __init__(self, *, result, validation_pending, corrections, **kwargs):
            self.result_value = result
            pending_states.append(validation_pending)

        def exec(self):
            return next(dialog_codes)

        def corrections(self):
            return {(2, "enero_usd"): "12.50"}

        def rows_to_import(self):
            return self.result_value.rows

    class ProgressDialog:
        def __init__(self, *, corrections, **kwargs):
            correction_requests.append(corrections)
            self.prepared_result, self.error_message = next(outcomes)

        def exec(self):
            return 0

        def deleteLater(self):
            pass

    def add_rows(rows, **kwargs):
        imported.extend(rows)
        return (0,)

    holder = SimpleNamespace(
        _workspace=SimpleNamespace(module_config=OPEX_MODULE_CONFIG, row_count=1, add_new_rows=add_rows),
        _excel_import_actor="tester", _excel_import_path="test.xlsx", _page_size=100,
        status_label=SimpleNamespace(setText=lambda text: None),
        _load_page=lambda index: None, _select_session_row=lambda index: None,
        workspace_changed=SimpleNamespace(emit=lambda: None),
    )
    monkeypatch.setattr(page_module, "BudgetExcelImportDialog", ReviewDialog)
    monkeypatch.setattr(page_module, "BudgetExcelRevalidationDialog", ProgressDialog)
    monkeypatch.setattr(page_module.AppMessageBox, "warning", lambda *args: None)
    page_module.PresupuestoPage._on_excel_import_loaded(holder, original)

    assert pending_states == [False, True, False]
    assert imported == [{"value": "corregido"}]
    assert correction_requests == [{(2, "enero_usd"): "12.50"}] * 2
    assert holder._excel_import_actor is None
