import argparse
import sys

from database.bootstrap.cleaner import (
    CleaningError,
)
from database.bootstrap.persistence_enricher import (
    PersistenceEnrichmentError,
)
from database.bootstrap.pipeline import (
    BootstrapPreparationError,
    prepare_budget,
)
from database.bootstrap.projector import (
    ProjectionError,
)
from database.bootstrap.source_loader import (
    SourceLoadError,
)


def parse_sheet(
    value: str,
):
    text = str(
        value
    ).strip()

    if text.isdigit():
        return int(
            text
        )

    return text


def print_issues(
    error: BootstrapPreparationError,
):
    result = (
        error.cleaning_result
    )

    if result is None:
        return

    if not result.issues:
        return

    print()
    print(
        "ERRORES DE LIMPIEZA"
    )
    print("-" * 80)

    limit = 20

    for issue in (
        result.issues[:limit]
    ):
        print(
            f"Fila {issue.row_number} | "
            f"{issue.column} | "
            f"{issue.value!r}"
        )

    remaining = (
        len(result.issues)
        - limit
    )

    if remaining > 0:
        print()
        print(
            f"... y {remaining} "
            "errores adicionales."
        )


def print_prepare_report(
    result,
):
    print()
    print("=" * 80)
    print(
        "PREPARACION DE PRESUPUESTO"
    )
    print("=" * 80)

    print()
    print(
        f"Archivo                 : "
        f"{result.source_path}"
    )

    print(
        f"Usuario                 : "
        f"{result.actor}"
    )

    print()
    print(
        f"Filas origen            : "
        f"{result.source_row_count:,}"
    )

    print(
        f"Columnas origen         : "
        f"{result.source_column_count:,}"
    )

    print(
        f"Columnas limpias        : "
        f"{result.cleaning.stats.column_count:,}"
    )

    print(
        f"Columnas almacenamiento : "
        f"{result.projection.column_count:,}"
    )

    print(
        f"Columnas finales        : "
        f"{result.final_column_count:,}"
    )

    print()
    print(
        f"Importes validos        : "
        f"{result.cleaning.stats.amount_count:,}"
    )

    print(
        f"Guiones convertidos     : "
        f"{result.cleaning.stats.dash_count:,}"
    )

    print(
        f"Importes NULL           : "
        f"{result.cleaning.stats.empty_amount_count:,}"
    )

    print(
        f"Errores                 : "
        f"{result.cleaning.stats.error_count:,}"
    )

    if (
        result.cleaning.extra_columns
    ):
        print()
        print(
            "Columnas adicionales "
            "ignoradas:"
        )

        for column in (
            result.cleaning.extra_columns
        ):
            print(
                f"  - {column}"
            )

    if (
        result.projection
        .dropped_columns
    ):
        print()
        print(
            "Columnas excluidas "
            "del almacenamiento:"
        )

        for column in (
            result.projection
            .dropped_columns
        ):
            print(
                f"  - {column}"
            )

    print()
    print(
        f"row_id generados        : "
        f"{len(result.dataframe):,}"
    )

    print(
        f"row_id unicos           : "
        f"{result.unique_row_id_count:,}"
    )

    print(
        "habilitado inicial     : TRUE"
    )

    print(
        "version inicial        : 1"
    )

    print()
    print(
        "RESULTADO               : OK"
    )

    print()
    print(
        "No se realizo ningun "
        "cambio en BigQuery."
    )
    print()


def run_prepare(
    args,
) -> int:
    sheet = parse_sheet(
        args.sheet
    )

    try:
        result = prepare_budget(
            args.file,
            actor=args.actor,
            sheet_name=sheet,
        )

    except BootstrapPreparationError as exc:
        print()
        print(
            "PREPARACION RECHAZADA"
        )
        print(str(exc))

        print_issues(
            exc
        )

        return 2

    except (
        SourceLoadError,
        CleaningError,
        ProjectionError,
        PersistenceEnrichmentError,
    ) as exc:
        print()
        print(
            "ERROR DE PREPARACION"
        )
        print(
            type(exc).__name__
        )
        print(
            str(exc)
        )

        return 2

    print_prepare_report(
        result
    )

    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="database",
        description=(
            "Herramientas de base de datos "
            "de APP Presupuesto TI."
        ),
    )

    subparsers = (
        parser.add_subparsers(
            dest="command",
            required=True,
        )
    )

    prepare_parser = (
        subparsers.add_parser(
            "prepare",
            help=(
                "Valida y prepara un "
                "presupuesto localmente."
            ),
        )
    )

    prepare_parser.add_argument(
        "--file",
        required=True,
        help=(
            "Archivo CSV, XLSX, "
            "XLSM o JSON."
        ),
    )

    prepare_parser.add_argument(
        "--actor",
        required=True,
        help=(
            "Usuario responsable "
            "de la preparacion."
        ),
    )

    prepare_parser.add_argument(
        "--sheet",
        default="0",
        help=(
            "Indice o nombre de la "
            "hoja Excel. Default: 0."
        ),
    )

    prepare_parser.set_defaults(
        handler=run_prepare
    )

    return parser


def main(
    argv=None,
) -> int:
    parser = build_parser()

    args = parser.parse_args(
        argv
    )

    return int(
        args.handler(
            args
        )
    )


if __name__ == "__main__":
    sys.exit(
        main()
    )