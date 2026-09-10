
import argparse
import sys
from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from app.config.settings import (
    settings,
)
from app.services.bigquery_service import (
    BigQueryService,
)
from database.migrations.staging_insert_support import (
    StagingInsertMigrationError,
    migrate_staging_insert_support,
)


def main(
    argv=None,
):
    parser = argparse.ArgumentParser(
        description=(
            "Agrega soporte UPDATE/INSERT "
            "a la tabla staging."
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
        result = (
            migrate_staging_insert_support(
                service.client,
                project=(
                    settings
                    .GOOGLE_CLOUD_PROJECT
                ),
                dataset=(
                    settings
                    .BIGQUERY_DATASET
                ),
                staging_table=(
                    settings
                    .BIGQUERY_STAGING_TABLE
                ),
                location=(
                    settings
                    .BIGQUERY_LOCATION
                ),
                apply=args.apply,
            )
        )

    except (
        StagingInsertMigrationError,
        Exception,
    ) as exc:
        print()
        print("ERROR")
        print(type(exc).__name__)
        print(str(exc))
        print()
        return 1

    print()
    print("=" * 72)

    print(
        "STAGING INSERT MIGRATION"
        if args.apply
        else
        "STAGING INSERT DRY RUN"
    )

    print("=" * 72)

    print(
        "Tabla      :",
        result.table_id,
    )

    print(
        "Estado     :",
        result.status,
    )

    print(
        "Existentes :",
        result.existing_columns,
    )

    print(
        "Agregar    :",
        result.added_columns,
    )

    print()

    if not args.apply:
        print(
            "No se modifico BigQuery."
        )

    else:
        print(
            "RESULTADO: MIGRACION OK"
        )

    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
