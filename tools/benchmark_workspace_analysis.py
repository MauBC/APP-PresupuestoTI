"""Offline: python -m tools.benchmark_workspace_analysis --rows 50000."""

import argparse
import json
from decimal import Decimal
from statistics import median
from time import perf_counter

from app.config.budget_modules import OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG
from app.services.presupuesto_workspace import PresupuestoWorkspace
from app.services.presupuesto_workspace_analysis_service import PresupuestoWorkspaceAnalysisService


def measure(config, size):
    def rows():
        for index in range(size):
            row = {column: None for column in config.dimension_columns}
            row.update({column: Decimal("1.000000001") for column in config.month_columns})
            row[config.annual_column] = Decimal("12.000000012")
            row[config.country_column] = "PERU" if index % 2 else "CHILE"
            row[config.budgeter_column] = f"Persona {index % 20}"
            row["habilitado"] = index % 5 != 0
            yield row

    workspace = PresupuestoWorkspace(config)
    started = perf_counter()
    workspace.load(rows())
    output = {"module": config.module.value, "rows": size, "load_seconds": round(perf_counter() - started, 6)}
    service = PresupuestoWorkspaceAnalysisService(workspace)
    operations = {
        "first_page": lambda: service.get_page(page_index=0, page_size=100),
        "out_of_range": lambda: service.get_page(page_index=size, page_size=100),
        "enabled_page": lambda: service.get_page(page_index=0, page_size=100, enabled_filter="enabled"),
        "enabled_out_of_range": lambda: service.get_page(page_index=size, page_size=100, enabled_filter="enabled"),
        "grouped": lambda: service.get_grouped_totals((config.country_column, config.budgeter_column)),
        "grouped_filtered": lambda: service.get_grouped_totals((config.country_column,), country_filter="PERU"),
    }
    for name, operation in operations.items():
        timings = []
        for _ in range(5):
            started = perf_counter()
            operation()
            timings.append(perf_counter() - started)
        output[name + "_seconds"] = round(median(timings), 6)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=50000)
    args = parser.parse_args()
    if args.rows <= 0:
        parser.error("rows must be positive")
    for config in (OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG):
        print(json.dumps(measure(config, args.rows)), flush=True)


if __name__ == "__main__":
    main()
