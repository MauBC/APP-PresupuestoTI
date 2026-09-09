import argparse
import sys

from app.config.settings import (
    settings,
)
from app.services.bigquery_service import (
    BigQueryService,
)
from database.migrations.reversal_reference import (
    ReversalReferenceMigrationError,
    migrate_reversal_reference,
)


def main(
    argv=None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Agrega reverted_batch_id a "
            "presupuesto_change_batches."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    args = parser.parse_args(
        argv
    )

    service = BigQueryService()

    try:
        result = migrate_reversal_reference(
            service.client,
            project=(
                settings.GOOGLE_CLOUD_PROJECT
            ),
            dataset=(
                settings.BIGQUERY_DATASET
            ),
            batch_table=(
                settings.BIGQUERY_BATCH_TABLE
            ),
            location=(
                settings.BIGQUERY_LOCATION
            ),
            apply=args.apply,
        )

    except ReversalReferenceMigrationError as exc:
        print()
        print(
            "ERROR DE MIGRACION"
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
        "REVERSAL REFERENCE MIGRATION"
        if args.apply
        else
        "REVERSAL REFERENCE DRY RUN"
    )

    print(
        "=" * 72
    )

    print(
        "Tabla          :",
        result.table_id,
    )

    print(
        "Estado         :",
        result.status,
    )

    print(
        "Columna previa :",
        result.column_existed,
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
