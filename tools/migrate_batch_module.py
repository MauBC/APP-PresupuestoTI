import argparse
import sys

from app.config.settings import (
    settings,
)
from app.services.bigquery_service import (
    BigQueryService,
)
from database.migrations.batch_module import (
    BatchModuleMigrationError,
    migrate_batch_module,
)


def main(
    argv=None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Agrega budget_module a "
            "presupuesto_change_batches "
            "y marca batches historicos "
            "como OPEX."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Ejecutar la migracion. "
            "Sin esta opcion solo valida."
        ),
    )

    args = parser.parse_args(
        argv
    )

    service = BigQueryService()

    try:
        result = migrate_batch_module(
            service.client,
            project=(
                settings
                .GOOGLE_CLOUD_PROJECT
            ),
            dataset=(
                settings
                .BIGQUERY_DATASET
            ),
            batch_table=(
                settings
                .BIGQUERY_BATCH_TABLE
            ),
            location=(
                settings
                .BIGQUERY_LOCATION
            ),
            apply=args.apply,
        )

    except (
        BatchModuleMigrationError,
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

    print()
    print(
        "=" * 72
    )

    print(
        "BATCH MODULE MIGRATION"
        if args.apply
        else
        "BATCH MODULE DRY RUN"
    )

    print(
        "=" * 72
    )

    print(
        f"Tabla          : "
        f"{result.table_id}"
    )

    print(
        f"Estado         : "
        f"{result.status}"
    )

    print(
        f"Columna previa : "
        f"{result.column_existed}"
    )

    if args.apply:
        print(
            f"Filas OPEX     : "
            f"{result.updated_rows}"
        )

    print()

    if args.apply:
        print(
            "RESULTADO: MIGRACION OK"
        )
    else:
        print(
            "RESULTADO: DRY RUN OK"
        )

        print(
            "No se modifico BigQuery."
        )

    print()

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
