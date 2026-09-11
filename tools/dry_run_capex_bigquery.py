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


from app.config.settings import (
    settings,
)
from database.bootstrap.capex_load_plan import (
    build_capex_load_plan,
)
from database.bootstrap.capex_pipeline import (
    prepare_capex_bootstrap,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Prepara CAPEX para BigQuery "
            "sin escribir en Google Cloud."
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
        "--expected-year",
        type=int,
        default=None,
        help=(
            "Omitir para archivos "
            "historicos/de simulacion."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Limita solo la validacion "
            "del load plan local."
        ),
    )

    args = parser.parse_args()

    print()
    print(
        "Preparando CAPEX..."
    )

    preparation = (
        prepare_capex_bootstrap(
            args.file,
            actor=args.actor,
            expected_year=(
                args.expected_year
            ),
        )
    )

    dataframe = (
        preparation.dataframe
    )

    if args.limit is not None:
        if args.limit < 1:
            raise ValueError(
                "--limit debe ser "
                "mayor que cero."
            )

        dataframe = (
            dataframe
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

    technical_nulls = {
        column:
            int(
                dataframe[
                    column
                ]
                .isna()
                .sum()
            )
        for column in (
            "row_id",
            "habilitado",
            "version",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        )
    }

    print()
    print(
        "=" * 80
    )
    print(
        "CAPEX BIGQUERY DRY-RUN"
    )
    print(
        "=" * 80
    )

    print(
        f"Archivo             : "
        f"{preparation.source_path}"
    )

    print(
        f"Filas Excel         : "
        f"{preparation.source_row_count}"
    )

    print(
        f"Filas preparadas    : "
        f"{preparation.final_row_count}"
    )

    print(
        f"Filas load plan     : "
        f"{plan.row_count}"
    )

    print(
        f"Columnas negocio    : "
        f"{preparation.business_column_count}"
    )

    print(
        f"Columnas finales    : "
        f"{plan.column_count}"
    )

    print(
        f"row_id unicos       : "
        f"{dataframe['row_id'].nunique()}"
    )

    print(
        f"Tabla destino       : "
        f"{plan.table_id}"
    )

    print(
        f"Location            : "
        f"{plan.location}"
    )

    print(
        f"Write disposition   : "
        f"{plan.write_disposition}"
    )

    print(
        f"Errores importacion : "
        f"{preparation.import_result.error_count}"
    )

    print(
        f"Advertencias        : "
        f"{preparation.import_result.warning_count}"
    )

    print(
        f"Informativos        : "
        f"{preparation.import_result.info_count}"
    )

    print()
    print(
        "NULL técnicos:"
    )

    for (
        column,
        count,
    ) in technical_nulls.items():
        print(
            f"  {column:<12}: "
            f"{count}"
        )

    print()
    print(
        "RESULTADO           : OK"
    )
    print(
        "BIGQUERY MODIFICADO : NO"
    )
    print()


if __name__ == "__main__":
    main()
