
import argparse
from itertools import count
from time import perf_counter
import tracemalloc

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from app.config.budget_modules import (
    get_budget_module_config,
)
from app.services.new_budget_row_service import (
    NewBudgetRowService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)


def mb(
    value,
):
    return (
        value
        / 1024
        / 1024
    )


def main():
    parser = (
        argparse.ArgumentParser(
            description=(
                "Benchmark local de altas "
                "masivas al Workspace."
            )
        )
    )

    parser.add_argument(
        "--module",
        choices=(
            "OPEX",
            "CAPEX",
        ),
        default="OPEX",
    )

    parser.add_argument(
        "--rows",
        type=int,
        default=1000,
    )

    args = parser.parse_args()

    if args.rows < 1:
        raise ValueError(
            "--rows debe ser > 0."
        )

    config = (
        get_budget_module_config(
            args.module
        )
    )

    sequence = count(
        1
    )

    row_service = (
        NewBudgetRowService(
            config,
            row_id_factory=(
                lambda:
                    "benchmark-"
                    f"{next(sequence)}"
            ),
        )
    )

    dimensions = {
        config.country_column:
            "PER",
    }

    dimensions = {
        key: value
        for key, value
        in dimensions.items()
        if key
    }

    workspace = (
        PresupuestoWorkspace(
            config
        )
    )

    workspace.load(
        ()
    )

    tracemalloc.start()

    build_started = (
        perf_counter()
    )

    rows = tuple(
        row_service
        .create_draft(
            dimensions,
            actor="benchmark",
        )
        .row
        for _ in range(
            args.rows
        )
    )

    build_seconds = (
        perf_counter()
        - build_started
    )

    workspace_started = (
        perf_counter()
    )

    workspace.add_new_rows(
        rows,
        description=(
            "Benchmark bulk import"
        ),
    )

    workspace_seconds = (
        perf_counter()
        - workspace_started
    )

    current, peak = (
        tracemalloc
        .get_traced_memory()
    )

    tracemalloc.stop()

    print()
    print("=" * 72)
    print("BULK WORKSPACE BENCHMARK")
    print("=" * 72)
    print(
        "Modulo              :",
        config.label,
    )
    print(
        "Filas               :",
        f"{args.rows:,}",
    )
    print(
        "Preparar drafts     :",
        f"{build_seconds:.4f} s",
    )
    print(
        "Agregar al Workspace:",
        f"{workspace_seconds:.4f} s",
    )
    print(
        "Historial local     :",
        workspace.history_count,
    )
    print(
        "Filas pendientes    :",
        workspace.pending_row_count,
    )
    print(
        "Memoria actual      :",
        f"{mb(current):.2f} MB",
    )
    print(
        "Pico memoria        :",
        f"{mb(peak):.2f} MB",
    )
    print("=" * 72)


if __name__ == "__main__":
    main()
