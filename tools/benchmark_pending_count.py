"""Offline benchmark: python -m tools.benchmark_pending_count --rows 50000 --dirty 5000."""
import argparse
import json
import tracemalloc
from decimal import Decimal
from statistics import median
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
    replacements = {}
    for index in range(dirty):
        row = workspace.get_row(index)
        for column in config.month_columns:
            row[column] = Decimal("1.000000001")
        row[config.annual_column] = Decimal("12.000000012")
        replacements[index] = row
    started = perf_counter()
    workspace.apply_batch(description="Offline benchmark", replacements=replacements)
    edit_seconds = perf_counter() - started
    expected = dirty * len(config.amount_columns)
    timings = []
    for _ in range(5):
        started = perf_counter()
        assert workspace.pending_change_count == expected
        timings.append(perf_counter() - started)
    tracemalloc.start()
    assert workspace.pending_change_count == expected
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    started = perf_counter()
    workspace.undo_last()
    undo_seconds = perf_counter() - started
    assert workspace.pending_change_count == 0
    return {"module": config.module.value, "rows": size, "dirty": dirty,
            "fields": expected, "batch_edit_seconds": round(edit_seconds, 4),
            "count_median_seconds": round(median(timings), 6),
            "count_python_peak_mb": round(peak / 1024**2, 3),
            "undo_seconds": round(undo_seconds, 4)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=50000)
    parser.add_argument("--dirty", type=int, default=5000)
    args = parser.parse_args()
    if not 0 <= args.dirty <= args.rows:
        parser.error("Require 0 <= dirty <= rows")
    for config in (OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG):
        print(json.dumps(measure(config, args.rows, args.dirty)), flush=True)


if __name__ == "__main__":
    main()
