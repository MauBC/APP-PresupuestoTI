import gc
import tracemalloc

from app.repositories.presupuesto_repository import (
    PresupuestoRepository,
)
from app.services.bigquery_service import (
    BigQueryService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_loader import (
    PresupuestoWorkspaceLoader,
)


def bytes_to_mb(value: int) -> float:
    return value / 1024 / 1024


def main():
    print("=" * 80)
    print("BENCHMARK WORKSPACE")
    print("=" * 80)

    bigquery = BigQueryService()

    repository = PresupuestoRepository(
        bigquery
    )

    workspace = PresupuestoWorkspace()

    loader = PresupuestoWorkspaceLoader(
        repository,
        workspace,
    )

    gc.collect()
    tracemalloc.start()

    before_current, before_peak = (
        tracemalloc.get_traced_memory()
    )

    result = loader.load()

    after_current, after_peak = (
        tracemalloc.get_traced_memory()
    )

    tracemalloc.stop()

    current_delta = (
        after_current - before_current
    )

    peak_delta = (
        after_peak - before_peak
    )

    print(
        f"Filas cargadas          : "
        f"{result.row_count:,}"
    )

    print(
        f"Lectura BigQuery        : "
        f"{result.fetch_seconds:.3f} s"
    )

    print(
        f"Carga Workspace         : "
        f"{result.workspace_seconds:.3f} s"
    )

    print(
        f"Tiempo total            : "
        f"{result.total_seconds:.3f} s"
    )

    print(
        f"Memoria Python actual   : "
        f"{bytes_to_mb(current_delta):.2f} MB"
    )

    print(
        f"Pico memoria Python     : "
        f"{bytes_to_mb(peak_delta):.2f} MB"
    )

    print(
        f"Filas Workspace         : "
        f"{workspace.row_count:,}"
    )

    print(
        f"Cambios pendientes      : "
        f"{workspace.pending_row_count}"
    )

    print(
        f"Historial               : "
        f"{workspace.history_count}"
    )

    print("=" * 80)


if __name__ == "__main__":
    main()