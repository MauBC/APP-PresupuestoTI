import argparse
import sys

from app.config.settings import (
    settings,
)
from app.services.bigquery_service import (
    BigQueryService,
)
from database.migrations.persistence_tables import (
    PersistenceMigrationError,
    ensure_persistence_tables,
)


def print_report(
    result,
    *,
    apply: bool,
):
    print()
    print("=" * 80)

    if apply:
        print(
            "PERSISTENCE TABLE MIGRATION"
        )
    else:
        print(
            "PERSISTENCE TABLE DRY RUN"
        )

    print("=" * 80)

    print(
        f"Project  : "
        f"{result.project}"
    )

    print(
        f"Dataset  : "
        f"{result.dataset}"
    )

    print(
        f"Location : "
        f"{result.location}"
    )

    print()

    for table in result.tables:
        print(
            f"{table.status:12} "
            f"{table.table_id}"
        )

    print()

    if apply:
        print(
            f"Creadas   : "
            f"{result.created_count}"
        )

        print(
            f"Existentes: "
            f"{result.existing_count}"
        )

    else:
        print(
            f"Existentes     : "
            f"{result.existing_count}"
        )

        print(
            f"Por crear      : "
            f"{result.pending_count}"
        )

    print()

    if apply:
        print(
            "RESULTADO: MIGRACION OK"
        )
    else:
        print(
            "RESULTADO: DRY RUN OK"
        )

        print()
        print(
            "No se realizo ningun "
            "cambio en BigQuery."
        )

    print()


def main(
    argv=None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Valida o crea las tablas "
            "auxiliares de persistencia."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Crear tablas faltantes. "
            "Sin esta opcion solo valida."
        ),
    )

    args = parser.parse_args(
        argv
    )

    service = (
        BigQueryService()
    )

    try:
        result = (
            ensure_persistence_tables(
                service.client,
                project=(
                    settings
                    .GOOGLE_CLOUD_PROJECT
                ),
                dataset=(
                    settings
                    .BIGQUERY_DATASET
                ),
                location=(
                    settings
                    .BIGQUERY_LOCATION
                ),
                apply=args.apply,
            )
        )

    except (
        PersistenceMigrationError,
        Exception,
    ) as exc:
        print()
        print(
            "ERROR DE MIGRACION"
        )

        print(
            type(exc).__name__
        )

        print(
            str(exc)
        )

        print()

        return 1

    print_report(
        result,
        apply=args.apply,
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
