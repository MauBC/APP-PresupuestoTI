import argparse
from decimal import Decimal
from pathlib import Path
import sys


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

if str(
    PROJECT_ROOT
) not in sys.path:
    sys.path.insert(
        0,
        str(
            PROJECT_ROOT
        ),
    )


from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
)
from app.repositories.presupuesto_repository import (
    PresupuestoRepository,
)
from app.services.bigquery_service import (
    BigQueryService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
    SESSION_ROW_ID,
)
from app.services.presupuesto_workspace_loader import (
    PresupuestoWorkspaceLoader,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Verifica la carga real de "
            "CAPEX en el Workspace sin "
            "modificar BigQuery."
        )
    )

    parser.add_argument(
        "--expected-rows",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--expected-year",
        type=int,
        default=None,
    )

    args = parser.parse_args()

    module_config = (
        CAPEX_MODULE_CONFIG
    )

    bigquery_service = (
        BigQueryService()
    )

    repository = (
        PresupuestoRepository(
            bigquery_service,
            module_config=(
                module_config
            ),
        )
    )

    workspace = (
        PresupuestoWorkspace(
            module_config
        )
    )

    loader = (
        PresupuestoWorkspaceLoader(
            repository,
            workspace,
        )
    )

    result = loader.load()

    rows = workspace.get_rows()

    if (
        result.row_count
        != args.expected_rows
    ):
        raise RuntimeError(
            "Cantidad CAPEX incorrecta. "
            f"Esperadas="
            f"{args.expected_rows}; "
            f"cargadas="
            f"{result.row_count}."
        )

    if (
        workspace.row_count
        != args.expected_rows
    ):
        raise RuntimeError(
            "El Workspace CAPEX no "
            "contiene las filas esperadas."
        )

    row_ids = tuple(
        str(
            row.get(
                "row_id",
                "",
            )
            or ""
        ).strip()
        for row in rows
    )

    if any(
        not row_id
        for row_id in row_ids
    ):
        raise RuntimeError(
            "El Workspace CAPEX contiene "
            "row_id vacios."
        )

    if (
        len(
            set(
                row_ids
            )
        )
        != len(
            row_ids
        )
    ):
        raise RuntimeError(
            "El Workspace CAPEX contiene "
            "row_id duplicados."
        )

    years = tuple(
        sorted(
            {
                int(
                    row[
                        "anio"
                    ]
                )
                for row in rows
                if row.get(
                    "anio"
                ) is not None
            }
        )
    )

    if (
        args.expected_year
        is not None
        and years
        != (
            args.expected_year,
        )
    ):
        raise RuntimeError(
            "El ano CAPEX cargado "
            "no coincide. "
            f"Esperado="
            f"{args.expected_year}; "
            f"encontrado={years}."
        )

    versions = {
        int(
            row[
                "version"
            ]
        )
        for row in rows
    }

    if versions != {
        1
    }:
        raise RuntimeError(
            "Las versiones CAPEX "
            f"no son iniciales: {versions}."
        )

    disabled = sum(
        1
        for row in rows
        if not bool(
            row[
                "habilitado"
            ]
        )
    )

    if disabled:
        raise RuntimeError(
            "Existen filas CAPEX "
            "deshabilitadas."
        )

    expected_loaded_columns = {
        *repository.load_columns,
        SESSION_ROW_ID,
    }

    for index, row in enumerate(
        rows
    ):
        if (
            set(
                row
            )
            != expected_loaded_columns
        ):
            raise RuntimeError(
                "La fila CAPEX "
                f"{index} no coincide con "
                "el contrato de Workspace."
            )

    sample_cebe = next(
        (
            row.get(
                "codigo_cebe"
            )
            for row in rows
            if row.get(
                "codigo_cebe"
            )
        ),
        None,
    )

    sample_ceco = next(
        (
            row.get(
                "codigo_ceco"
            )
            for row in rows
            if row.get(
                "codigo_ceco"
            )
        ),
        None,
    )

    amount_samples = []

    for row in rows:
        for column in (
            module_config
            .amount_columns
        ):
            value = row.get(
                column
            )

            if value is not None:
                amount_samples.append(
                    value
                )

            if (
                len(
                    amount_samples
                )
                >= 5
            ):
                break

        if (
            len(
                amount_samples
            )
            >= 5
        ):
            break

    decimal_samples = sum(
        1
        for value in amount_samples
        if isinstance(
            value,
            Decimal,
        )
    )

    print()
    print(
        "=" * 80
    )
    print(
        "CAPEX WORKSPACE LOAD"
    )
    print(
        "=" * 80
    )

    print(
        f"Modulo             : "
        f"{module_config.label}"
    )

    print(
        f"Tabla              : "
        f"{module_config.main_table}"
    )

    print(
        f"Filas BigQuery     : "
        f"{result.row_count}"
    )

    print(
        f"Filas Workspace    : "
        f"{workspace.row_count}"
    )

    print(
        f"Dimensiones        : "
        f"{len(module_config.dimension_columns)}"
    )

    print(
        f"Importes activos   : "
        f"{len(module_config.amount_columns)}"
    )

    print(
        f"Columnas repository: "
        f"{len(repository.load_columns)}"
    )

    print(
        f"row_id unicos      : "
        f"{len(set(row_ids))}"
    )

    print(
        f"Anios              : "
        f"{years}"
    )

    print(
        f"Versiones          : "
        f"{tuple(sorted(versions))}"
    )

    print(
        f"Deshabilitadas     : "
        f"{disabled}"
    )

    print(
        f"Codigo CEBE muestra: "
        f"{sample_cebe!r}"
    )

    print(
        f"Codigo CECO muestra: "
        f"{sample_ceco!r}"
    )

    print(
        f"Decimal muestras   : "
        f"{decimal_samples}/"
        f"{len(amount_samples)}"
    )

    print(
        f"Fetch BigQuery     : "
        f"{result.fetch_seconds:.2f} s"
    )

    print(
        f"Workspace          : "
        f"{result.workspace_seconds:.2f} s"
    )

    print(
        f"Total              : "
        f"{result.total_seconds:.2f} s"
    )

    print()
    print(
        "RESULTADO          : OK"
    )

    print(
        "BIGQUERY MODIFICADO: NO"
    )

    print()


if __name__ == "__main__":
    main()
