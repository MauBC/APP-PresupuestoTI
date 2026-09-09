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

from app.config.settings import settings
from database.bootstrap.capex_load_plan import (
    build_capex_load_plan,
)
from database.bootstrap.capex_pipeline import (
    prepare_capex_bootstrap,
)
from database.bootstrap.capex_smoke_bigquery import (
    run_capex_bigquery_smoke_test,
)
from database.migrations.capex_main_table import (
    capex_schema_matches,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Smoke test temporal "
            "CAPEX en BigQuery."
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
        "--limit",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Carga temporalmente las filas, "
            "valida y las elimina."
        ),
    )

    args = parser.parse_args()

    if (
        args.limit < 1
        or args.limit > 20
    ):
        raise ValueError(
            "--limit debe estar "
            "entre 1 y 20."
        )

    preparation = (
        prepare_capex_bootstrap(
            args.file,
            actor=args.actor,
            expected_year=None,
        )
    )

    dataframe = (
        preparation.dataframe
        .head(
            args.limit
        )
        .copy()
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
            "El schema CAPEX remoto "
            "no coincide."
        )

    print()
    print(
        "=" * 80
    )
    print(
        "CAPEX BIGQUERY SMOKE TEST"
    )
    print(
        "=" * 80
    )

    print(
        f"Tabla          : "
        f"{plan.table_id}"
    )

    print(
        f"Filas prueba   : "
        f"{len(dataframe)}"
    )

    print(
        f"Columnas       : "
        f"{plan.column_count}"
    )

    print(
        f"Schema         : OK"
    )

    if not args.apply:
        print(
            f"Modo           : DRY-RUN"
        )
        print(
            "BIGQUERY MODIFICADO: NO"
        )
        print()
        return

    result = (
        run_capex_bigquery_smoke_test(
            client,
            dataframe,
            table_id=plan.table_id,
            location=plan.location,
        )
    )

    print(
        f"Modo           : APPLY TEMPORAL"
    )

    print()
    print(
        "VALIDACION"
    )

    print(
        f"Filas cargadas : "
        f"{result.rows_loaded}"
    )

    print(
        f"Filas leidas   : "
        f"{result.selected_rows}"
    )

    print(
        f"row_id unicos  : "
        f"{result.unique_row_ids}"
    )

    print(
        f"Deshabilitadas : "
        f"{result.disabled_rows}"
    )

    print(
        f"Version min    : "
        f"{result.min_version}"
    )

    print(
        f"Version max    : "
        f"{result.max_version}"
    )

    print()
    print(
        "CLEANUP"
    )

    print(
        f"Filas antes    : "
        f"{result.preexisting_rows}"
    )

    print(
        f"Filas despues  : "
        f"{result.final_rows}"
    )

    print(
        f"Restaurada     : "
        f"{result.cleanup_ok}"
    )

    print()
    print(
        "RESULTADO      : OK"
    )
    print(
        "BIGQUERY QUEDO VACIO: "
        f"{result.final_rows == 0}"
    )
    print()


if __name__ == "__main__":
    main()
