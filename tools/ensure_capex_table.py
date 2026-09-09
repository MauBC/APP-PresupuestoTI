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

from app.config.settings import (
    settings,
)
from database.migrations.capex_main_table import (
    ensure_capex_main_table,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Inspecciona o crea la tabla "
            "principal CAPEX."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Crea la tabla si no existe. "
            "Sin este flag no modifica "
            "BigQuery."
        ),
    )

    args = parser.parse_args()

    project = (
        settings
        .GOOGLE_CLOUD_PROJECT
    )

    dataset = (
        settings
        .BIGQUERY_DATASET
    )

    table = (
        settings
        .BIGQUERY_CAPEX_TABLE
    )

    location = (
        settings
        .BIGQUERY_LOCATION
    )

    client = bigquery.Client(
        project=project,
        location=location,
    )

    result = (
        ensure_capex_main_table(
            client,
            project=project,
            dataset=dataset,
            table=table,
            location=location,
            apply=args.apply,
        )
    )

    print()
    print(
        "=" * 80
    )
    print(
        "CAPEX MAIN TABLE"
    )
    print(
        "=" * 80
    )

    print(
        f"Tabla            : "
        f"{result.table_id}"
    )

    print(
        f"Existe           : "
        f"{result.exists}"
    )

    print(
        f"Schema coincide  : "
        f"{result.schema_matches}"
    )

    print(
        f"Columnas         : "
        f"{result.column_count}"
    )

    print(
        f"Creada ahora     : "
        f"{result.created}"
    )

    print(
        f"Modo             : "
        f"{'APPLY' if args.apply else 'DRY-RUN'}"
    )

    print()

    if (
        not args.apply
        and not result.exists
    ):
        print(
            "RESULTADO         : "
            "LISTA PARA CREAR"
        )
        print(
            "BIGQUERY MODIFICADO: NO"
        )

    else:
        print(
            "RESULTADO         : OK"
        )

        print(
            "BIGQUERY MODIFICADO: "
            f"{'SI' if result.created else 'NO'}"
        )

    print()


if __name__ == "__main__":
    main()
