"""Offline: python -m tools.benchmark_workspace_discard --rows 50000 --dirty 1."""
import argparse
import json
import tracemalloc
from decimal import Decimal
from time import perf_counter

from app.config.budget_modules import OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG
from app.services.presupuesto_workspace import PresupuestoWorkspace


def measure(config, size, dirty):
    workspace = PresupuestoWorkspace(config)
    workspace.load(
        {**{column: None for column in config.dimension_columns},
         **{column: Decimal("0") for column in config.amount_columns}}
        for _ in range(size)
    )

    def edit():
        for index in range(dirty):
            workspace.edit_month(index, config.month_columns[0], Decimal("1.25"))

    edit()
    started = perf_counter()
    workspace.discard_all()
    seconds = perf_counter() - started
    edit()
    tracemalloc.start()
    workspace.discard_all()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert workspace.row_count == size
    assert workspace.pending_row_count == workspace.history_count == 0
    assert all(row[config.annual_column] == 0 for row in workspace.iter_rows())
    return {"module": config.module.value, "rows": size, "dirty": dirty,
            "discard_seconds": round(seconds, 6),
            "discard_python_peak_mb": round(peak / 1024**2, 4)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=50000)
    parser.add_argument("--dirty", type=int, default=1)
    args = parser.parse_args()
    if not 0 <= args.dirty <= args.rows:
        parser.error("Require 0 <= dirty <= rows")
    for config in (OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG):
        print(json.dumps(measure(config, args.rows, args.dirty)), flush=True)


if __name__ == "__main__":
    main()
