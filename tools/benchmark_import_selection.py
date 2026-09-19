"""Offline benchmark: python -m tools.benchmark_import_selection --rows 50000."""

import argparse
import json
import tracemalloc
from time import perf_counter

from PySide6.QtWidgets import QApplication

from app.config.budget_modules import CAPEX_MODULE_CONFIG, OPEX_MODULE_CONFIG
from app.ui.models.budget_import_preview_model import BudgetImportPreviewModel
from app.models.budget_excel_import import BudgetExcelImportResult
from app.ui.dialogs.budget_excel_import_dialog import BudgetExcelImportDialog


def measure_dialog(config, size):
    ceco = "ceco" if config == OPEX_MODULE_CONFIG else "codigo_ceco"
    rows = tuple({ceco: f"51{i:08d}"} for i in range(size))
    result = BudgetExcelImportResult(config.module.value, "synthetic.xlsx", "Sheet1", size, 1, rows)
    started = perf_counter()
    dialog = BudgetExcelImportDialog(result=result, module_config=config)
    load_seconds = perf_counter() - started
    try:
        dialog._preview_table.selectAll()
        started = perf_counter()
        dialog._exclude_selected_preview_rows()
        exclude_seconds = perf_counter() - started
        assert dialog._preview_model.included_count == 0
        assert not dialog._import_button.isEnabled()
        started = perf_counter()
        dialog._include_all_preview_rows()
        restore_seconds = perf_counter() - started
        assert dialog._preview_model.included_count == size
        return {
            "module": config.module.value, "dialog_rows": size,
            "load_seconds": round(load_seconds, 4),
            "exclude_all_seconds": round(exclude_seconds, 4),
            "restore_seconds": round(restore_seconds, 4),
        }
    finally:
        dialog.close()


def measure(config, size, selected):
    ceco = "ceco" if config == OPEX_MODULE_CONFIG else "codigo_ceco"
    tracemalloc.start()
    started = perf_counter()
    model = BudgetImportPreviewModel(
        rows=({ceco: f"51{i:08d}"} for i in range(size)), module_config=config,
    )
    load_seconds = perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    notifications = []

    def update_counts(*_):
        notifications.append((model.included_count, model.excluded_count))

    model.dataChanged.connect(update_counts)
    started = perf_counter()
    model.set_rows_included(range(selected), False)
    exclude_seconds = perf_counter() - started
    assert model.included_count == size - selected
    assert model.excluded_source_rows() == frozenset(range(2, selected + 2))
    started = perf_counter()
    model.include_all()
    restore_seconds = perf_counter() - started
    assert model.included_count == size and not model.excluded_source_rows()
    return {
        "module": config.module.value, "rows": size, "selected": selected,
        "load_seconds_with_tracemalloc": round(load_seconds, 4),
        "python_peak_mb": round(peak / 1024**2, 2),
        "exclude_seconds": round(exclude_seconds, 4),
        "include_all_seconds": round(restore_seconds, 4),
        "notifications": len(notifications),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=50000)
    parser.add_argument("--selected", type=int, default=None)
    parser.add_argument("--dialog", action="store_true", help="Also measure the complete dialog")
    args = parser.parse_args()
    selected = args.rows if args.selected is None else args.selected
    if not 0 <= selected <= args.rows:
        parser.error("Require 0 <= selected <= rows")
    app = QApplication.instance() or QApplication([])
    for config in (OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG):
        print(json.dumps(measure(config, args.rows, selected)), flush=True)
        if args.dialog:
            print(json.dumps(measure_dialog(config, args.rows)), flush=True)
    return app


if __name__ == "__main__":
    main()
