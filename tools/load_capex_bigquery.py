import argparse
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


from google.cloud import bigquery

from app.config.capex_schema import (
    CAPEX_EXPECTED_YEAR,
)
from app.config.settings import (
    settings,
)
from database.bootstrap.capex_full_load_bigquery import (
    get_capex_table_row_count,
    run_capex_full_load,
)
from database.bootstrap.capex_load_plan import (
    build_capex_load_plan,
)
from database.bootstrap.capex_pipeline import (
    prepare_capex_bootstrap,
)
from database.migrations.capex_main_table import (
    capex_schema_matches,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Carga completa y controlada "
            "de CAPEX a BigQuery."
        )
    )

    parser.add_argument(
        "--file",
        required=True,
    )

    parser.add_argument(
        "--actor",
        required=True,
    )

    parser.add_argument(
        "--expected-rows",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--simulation",
        action="store_true",
        help=(
            "Permite usar datos historicos "
            "sin exigir Ano=2027."
        ),
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Ejecuta la carga definitiva. "
            "Sin este flag solo valida."
        ),
    )

    args = parser.parse_args()

    if args.expected_rows < 1:
        raise ValueError(
            "--expected-rows debe ser "
            "mayor que cero."
        )

    expected_year = (
        None
        if args.simulation
        else CAPEX_EXPECTED_YEAR
    )

    preparation = (
        prepare_capex_bootstrap(
            args.file,
            actor=args.actor,
            expected_year=(
                expected_year
            ),
        )
    )

    dataframe = (
        preparation.dataframe
    )

    plan = (
        build_capex_load_plan(
            dataframe,
            project=(
                settings
                .GOOGLE_CLOUD_PROJECT
            ),
            dataset=(
                settings
                .BIGQUERY_DATASET
            ),
            table=(
                settings
                .BIGQUERY_CAPEX_TABLE
            ),
            location=(
                settings
                .BIGQUERY_LOCATION
            ),
        )
    )

    if (
        plan.row_count
        != args.expected_rows
    ):
        raise RuntimeError(
            "El Excel no tiene la cantidad "
            "de filas esperada. "
            f"Esperadas="
            f"{args.expected_rows}; "
            f"preparadas="
            f"{plan.row_count}."
        )

    years = tuple(
        sorted(
            {
                int(
                    value
                )
                for value
                in dataframe[
                    "anio"
                ]
                .dropna()
                .tolist()
            }
        )
    )

    client = bigquery.Client(
        project=plan.project,
        location=plan.location,
    )

    table = client.get_table(
        plan.table_id
    )

    if not capex_schema_matches(
        table.schema
    ):
        raise RuntimeError(
            "El schema remoto CAPEX "
            "no coincide."
        )

    existing_rows = (
        get_capex_table_row_count(
            client,
            table_id=plan.table_id,
            location=plan.location,
        )
    )

    if existing_rows != 0:
        raise RuntimeError(
            "La tabla CAPEX no esta vacia. "
            f"Filas actuales="
            f"{existing_rows}."
        )

    print()
    print(
        "=" * 80
    )
    print(
        "CAPEX FULL LOAD"
    )
    print(
        "=" * 80
    )

    print(
        f"Archivo          : "
        f"{preparation.source_path}"
    )

    print(
        f"Tabla            : "
        f"{plan.table_id}"
    )

    print(
        f"Filas preparadas : "
        f"{plan.row_count}"
    )

    print(
        f"Columnas         : "
        f"{plan.column_count}"
    )

    print(
        f"row_id unicos    : "
        f"{preparation.unique_row_id_count}"
    )

    print(
        f"Anios detectados : "
        f"{years}"
    )

    print(
        f"Errores          : "
        f"{preparation.import_result.error_count}"
    )

    print(
        f"Advertencias     : "
        f"{preparation.import_result.warning_count}"
    )

    print(
        f"Informativos     : "
        f"{preparation.import_result.info_count}"
    )

    print(
        f"Tabla inicial    : "
        f"{existing_rows} filas"
    )

    print(
        f"Simulacion       : "
        f"{args.simulation}"
    )

    if not args.apply:
        print(
            f"Modo             : DRY-RUN"
        )
        print()
        print(
            "RESULTADO        : "
            "LISTO PARA CARGAR"
        )
        print(
            "BIGQUERY MODIFICADO: NO"
        )
        print()
        return

    result = (
        run_capex_full_load(
            client,
            dataframe,
            table_id=plan.table_id,
            location=plan.location,
            expected_rows=(
                args.expected_rows
            ),
            expected_year=(
                expected_year
            ),
        )
    )

    print()
    print(
        "VALIDACION BIGQUERY"
    )
    print(
        "-" * 80
    )

    print(
        f"Filas cargadas   : "
        f"{result.rows_loaded}"
    )

    print(
        f"Filas totales    : "
        f"{result.total_rows}"
    )

    print(
        f"row_id unicos    : "
        f"{result.unique_row_ids}"
    )

    print(
        f"Deshabilitadas   : "
        f"{result.disabled_rows}"
    )

    print(
        f"Version minima   : "
        f"{result.min_version}"
    )

    print(
        f"Version maxima   : "
        f"{result.max_version}"
    )

    print(
        f"Anios BigQuery   : "
        f"{result.years}"
    )

    print()
    print(
        "RESULTADO        : OK"
    )
    print(
        "CARGA PERMANECE EN BIGQUERY: SI"
    )
    print()


if __name__ == "__main__":
    main()
