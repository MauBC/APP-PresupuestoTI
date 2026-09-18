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


from app.config.settings import settings
from app.services.bigquery_service import (
    BigQueryService,
)
from database.migrations.capex_presupuestador import (
    migrate_capex_presupuestador,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Agrega Presupuestador "
            "al contrato CAPEX."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    args = parser.parse_args()

    service = BigQueryService()

    result = (
        migrate_capex_presupuestador(
            service.client,
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
            apply=args.apply,
        )
    )

    print()
    print("=" * 80)
    print("CAPEX PRESUPUESTADOR MIGRATION")
    print("=" * 80)
    print("Tabla :", result.table_id)
    print("Estado:", result.status)
    print(
        "Existia:",
        result.column_existed,
    )


if __name__ == "__main__":
    main()
