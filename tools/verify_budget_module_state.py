import argparse
from pathlib import Path
import sys

from google.cloud import bigquery


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


from app.config.budget_modules import (
    get_budget_module_config,
)
from app.config.settings import settings
from app.services.bigquery_service import (
    BigQueryService,
)


def query(
    client,
    sql,
    *,
    parameters=(),
):
    config = bigquery.QueryJobConfig(
        query_parameters=list(
            parameters
        )
    )

    return list(
        client.query(
            sql,
            job_config=config,
            location=(
                settings
                .BIGQUERY_LOCATION
            ),
        ).result()
    )


def full_table_id(
    table,
):
    return (
        f"{settings.GOOGLE_CLOUD_PROJECT}."
        f"{settings.BIGQUERY_DATASET}."
        f"{table}"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Verifica en modo read-only "
            "el estado de OPEX o CAPEX."
        )
    )

    parser.add_argument(
        "--module",
        required=True,
        choices=(
            "OPEX",
            "CAPEX",
        ),
    )

    parser.add_argument(
        "--expect-rows",
        type=int,
        default=None,
    )

    args = parser.parse_args()

    module = (
        get_budget_module_config(
            args.module
        )
    )

    service = BigQueryService()

    client = service.client

    main_table = full_table_id(
        module.main_table
    )

    table = client.get_table(
        main_table
    )

    schema_names = {
        field.name
        for field in table.schema
    }

    required = {
        "row_id",
        "habilitado",
        "version",
        *module.amount_columns,
    }

    missing = sorted(
        required
        - schema_names
    )

    sql = f"""
        SELECT
            COUNT(*) AS total_rows,

            COUNT(
                DISTINCT row_id
            ) AS unique_row_ids,

            COUNTIF(
                row_id IS NULL
                OR TRIM(row_id) = ''
            ) AS invalid_row_ids,

            COUNTIF(
                habilitado IS NULL
            ) AS invalid_habilitado,

            COUNTIF(
                version IS NULL
                OR version < 1
            ) AS invalid_versions,

            COUNTIF(
                habilitado = FALSE
            ) AS disabled_rows,

            MIN(version)
                AS min_version,

            MAX(version)
                AS max_version,

            COALESCE(
                SUM(
                    COALESCE(
                        `{module.annual_column}`,
                        NUMERIC '0'
                    )
                ),
                NUMERIC '0'
            ) AS annual_total

        FROM `{main_table}`
    """

    row = query(
        client,
        sql,
    )[0]

    total_rows = int(
        row["total_rows"]
    )

    unique_row_ids = int(
        row["unique_row_ids"]
    )

    issues = []

    if missing:
        issues.append(
            "Columnas faltantes: "
            + ", ".join(missing)
        )

    if (
        total_rows
        != unique_row_ids
    ):
        issues.append(
            "row_id no son unicos."
        )

    if int(
        row["invalid_row_ids"]
    ):
        issues.append(
            "Hay row_id invalidos."
        )

    if int(
        row["invalid_habilitado"]
    ):
        issues.append(
            "Hay habilitado NULL."
        )

    if int(
        row["invalid_versions"]
    ):
        issues.append(
            "Hay versiones invalidas."
        )

    if (
        args.expect_rows
        is not None
        and total_rows
        != args.expect_rows
    ):
        issues.append(
            "Filas distintas a lo esperado: "
            f"{total_rows} != "
            f"{args.expect_rows}."
        )

    batch_table = full_table_id(
        settings.BIGQUERY_BATCH_TABLE
    )

    staging_table = full_table_id(
        settings.BIGQUERY_STAGING_TABLE
    )

    audit_table = full_table_id(
        settings.BIGQUERY_AUDIT_TABLE
    )

    module_param = (
        bigquery.ScalarQueryParameter(
            "budget_module",
            "STRING",
            module.module.value,
        )
    )

    batches = query(
        client,
        f"""
        SELECT
            status,
            COUNT(*) AS total,
            COUNTIF(
                reverted_batch_id
                IS NOT NULL
            ) AS reversals
        FROM `{batch_table}`
        WHERE
            budget_module
            = @budget_module
        GROUP BY status
        ORDER BY status
        """,
        parameters=(
            module_param,
        ),
    )

    audit_count = int(
        query(
            client,
            f"""
            SELECT
                COUNT(*) AS total
            FROM `{audit_table}` a
            INNER JOIN `{batch_table}` b
                ON b.batch_id = a.batch_id
            WHERE
                b.budget_module
                = @budget_module
            """,
            parameters=(
                module_param,
            ),
        )[0]["total"]
    )

    staging_count = int(
        query(
            client,
            f"""
            SELECT
                COUNT(*) AS total
            FROM `{staging_table}` s
            INNER JOIN `{batch_table}` b
                ON b.batch_id = s.batch_id
            WHERE
                b.budget_module
                = @budget_module
            """,
            parameters=(
                module_param,
            ),
        )[0]["total"]
    )

    print()
    print("=" * 80)
    print(
        "BUDGET MODULE STATE"
    )
    print("=" * 80)

    print(
        f"Modulo          : "
        f"{module.label}"
    )

    print(
        f"Tabla           : "
        f"{main_table}"
    )

    print(
        f"Filas           : "
        f"{total_rows:,}"
    )

    print(
        f"row_id unicos   : "
        f"{unique_row_ids:,}"
    )

    print(
        f"Deshabilitados  : "
        f"{int(row['disabled_rows']):,}"
    )

    print(
        f"Version minima  : "
        f"{row['min_version']}"
    )

    print(
        f"Version maxima  : "
        f"{row['max_version']}"
    )

    print(
        f"Total anual USD : "
        f"{row['annual_total']}"
    )

    print(
        f"Audit rows      : "
        f"{audit_count:,}"
    )

    print(
        f"Staging rows    : "
        f"{staging_count:,}"
    )

    print()
    print("Batches")

    if not batches:
        print(
            "  Sin batches."
        )

    for batch in batches:
        print(
            f"  {batch['status']:<10}"
            f" {int(batch['total']):>6,}"
            f" | reversions="
            f"{int(batch['reversals']):,}"
        )

    print()

    if staging_count:
        print(
            "NOTA: staging puede contener "
            "filas de batches FAILED para "
            "diagnostico."
        )
        print()

    if issues:
        print(
            "RESULTADO       : ERROR"
        )

        for issue in issues:
            print(
                " -",
                issue,
            )

        return 1

    print(
        "RESULTADO       : OK"
    )

    print(
        "MODO            : READ-ONLY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
