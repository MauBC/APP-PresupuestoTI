import argparse
from datetime import datetime

from google.cloud import bigquery

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
)
from app.config.settings import settings


CONFIRM_TEXT = "RESET-CAPEX-2027"


def table_id(
    table_name,
):
    return (
        f"{settings.GOOGLE_CLOUD_PROJECT}."
        f"{settings.BIGQUERY_DATASET}."
        f"{table_name}"
    )


def scalar_count(
    client,
    sql,
):
    rows = client.query(
        sql,
        location=settings.BIGQUERY_LOCATION,
    ).result()

    row = next(
        iter(rows)
    )

    try:
        value = row["total"]

    except (
        KeyError,
        TypeError,
    ):
        value = row.total

    return int(
        value or 0
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Reset controlado de CAPEX "
            "antes de cargar la data real 2027."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Ejecuta el reset. "
            "Sin este flag solo muestra "
            "el diagnostico."
        ),
    )

    parser.add_argument(
        "--confirm",
        default="",
        help=(
            "Confirmacion requerida para "
            "operacion destructiva."
        ),
    )

    args = parser.parse_args()

    project = (
        settings.GOOGLE_CLOUD_PROJECT
    )

    dataset = (
        settings.BIGQUERY_DATASET
    )

    location = (
        settings.BIGQUERY_LOCATION
    )

    module = (
        CAPEX_MODULE_CONFIG
        .module
        .value
    )

    main_table = table_id(
        CAPEX_MODULE_CONFIG.main_table
    )

    batch_table = table_id(
        settings.BIGQUERY_BATCH_TABLE
    )

    audit_table = table_id(
        settings.BIGQUERY_AUDIT_TABLE
    )

    staging_table = table_id(
        settings.BIGQUERY_STAGING_TABLE
    )

    client = bigquery.Client(
        project=project
    )

    print()
    print("=" * 86)
    print("CAPEX 2027 - CUTOVER")
    print("=" * 86)
    print(
        f"Proyecto : {project}"
    )
    print(
        f"Dataset  : {dataset}"
    )
    print(
        f"Location : {location}"
    )
    print(
        f"Modulo   : {module}"
    )
    print(
        f"Tabla    : {main_table}"
    )
    print("=" * 86)

    capex_rows = scalar_count(
        client,
        f"""
        SELECT
            COUNT(*) AS total
        FROM `{main_table}`
        """,
    )

    capex_batches = scalar_count(
        client,
        f"""
        SELECT
            COUNT(*) AS total
        FROM `{batch_table}`
        WHERE
            budget_module = '{module}'
        """,
    )

    capex_audits = scalar_count(
        client,
        f"""
        SELECT
            COUNT(*) AS total
        FROM `{audit_table}` AS audit
        WHERE EXISTS (
            SELECT 1
            FROM `{batch_table}` AS batch
            WHERE
                batch.batch_id
                    = audit.batch_id
                AND batch.budget_module
                    = '{module}'
        )
        """,
    )

    capex_staging = scalar_count(
        client,
        f"""
        SELECT
            COUNT(*) AS total
        FROM `{staging_table}` AS staging
        WHERE EXISTS (
            SELECT 1
            FROM `{batch_table}` AS batch
            WHERE
                batch.batch_id
                    = staging.batch_id
                AND batch.budget_module
                    = '{module}'
        )
        """,
    )

    opex_batches = scalar_count(
        client,
        f"""
        SELECT
            COUNT(*) AS total
        FROM `{batch_table}`
        WHERE
            COALESCE(
                budget_module,
                'OPEX'
            ) = 'OPEX'
        """,
    )

    print()
    print("ESTADO ACTUAL")
    print(
        f"CAPEX filas principales : "
        f"{capex_rows:,}"
    )
    print(
        f"CAPEX batches           : "
        f"{capex_batches:,}"
    )
    print(
        f"CAPEX auditorias        : "
        f"{capex_audits:,}"
    )
    print(
        f"CAPEX staging           : "
        f"{capex_staging:,}"
    )
    print(
        f"OPEX batches protegidos : "
        f"{opex_batches:,}"
    )

    if not args.apply:
        print()
        print(
            "[DRY-RUN] No se elimino nada."
        )
        print(
            "Para ejecutar:"
        )
        print(
            "python -m tools."
            "reset_capex_for_real_load "
            "--apply "
            f"--confirm {CONFIRM_TEXT}"
        )
        return

    if (
        args.confirm
        != CONFIRM_TEXT
    ):
        raise RuntimeError(
            "Confirmacion incorrecta. "
            "Reset cancelado."
        )

    timestamp = (
        datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    backup_main = table_id(
        f"_backup_capex_"
        f"{timestamp}_main"
    )

    backup_batches = table_id(
        f"_backup_capex_"
        f"{timestamp}_batches"
    )

    backup_audit = table_id(
        f"_backup_capex_"
        f"{timestamp}_audit"
    )

    backup_staging = table_id(
        f"_backup_capex_"
        f"{timestamp}_staging"
    )

    print()
    print(
        "Creando backup temporal "
        "de 7 dias..."
    )

    backup_queries = (
        f"""
        CREATE TABLE `{backup_main}`
        OPTIONS (
            expiration_timestamp =
                TIMESTAMP_ADD(
                    CURRENT_TIMESTAMP(),
                    INTERVAL 7 DAY
                )
        )
        AS
        SELECT *
        FROM `{main_table}`
        """,

        f"""
        CREATE TABLE `{backup_batches}`
        OPTIONS (
            expiration_timestamp =
                TIMESTAMP_ADD(
                    CURRENT_TIMESTAMP(),
                    INTERVAL 7 DAY
                )
        )
        AS
        SELECT *
        FROM `{batch_table}`
        WHERE
            budget_module = '{module}'
        """,

        f"""
        CREATE TABLE `{backup_audit}`
        OPTIONS (
            expiration_timestamp =
                TIMESTAMP_ADD(
                    CURRENT_TIMESTAMP(),
                    INTERVAL 7 DAY
                )
        )
        AS
        SELECT audit.*
        FROM `{audit_table}` AS audit
        INNER JOIN `{batch_table}` AS batch
            ON batch.batch_id
                = audit.batch_id
        WHERE
            batch.budget_module
                = '{module}'
        """,

        f"""
        CREATE TABLE `{backup_staging}`
        OPTIONS (
            expiration_timestamp =
                TIMESTAMP_ADD(
                    CURRENT_TIMESTAMP(),
                    INTERVAL 7 DAY
                )
        )
        AS
        SELECT staging.*
        FROM `{staging_table}` AS staging
        INNER JOIN `{batch_table}` AS batch
            ON batch.batch_id
                = staging.batch_id
        WHERE
            batch.budget_module
                = '{module}'
        """,
    )

    for query in backup_queries:
        client.query(
            query,
            location=location,
        ).result()

    print(
        "[OK] Backup temporal creado."
    )

    reset_sql = f"""
        BEGIN TRANSACTION;

        DELETE FROM `{audit_table}`
        WHERE batch_id IN (
            SELECT batch_id
            FROM `{batch_table}`
            WHERE
                budget_module
                    = '{module}'
        );

        DELETE FROM `{staging_table}`
        WHERE batch_id IN (
            SELECT batch_id
            FROM `{batch_table}`
            WHERE
                budget_module
                    = '{module}'
        );

        DELETE FROM `{batch_table}`
        WHERE
            budget_module
                = '{module}';

        DELETE FROM `{main_table}`
        WHERE TRUE;

        COMMIT TRANSACTION;
    """

    print()
    print(
        "Ejecutando reset CAPEX..."
    )

    client.query(
        reset_sql,
        location=location,
    ).result()

    remaining_main = scalar_count(
        client,
        f"""
        SELECT COUNT(*) AS total
        FROM `{main_table}`
        """,
    )

    remaining_batches = scalar_count(
        client,
        f"""
        SELECT COUNT(*) AS total
        FROM `{batch_table}`
        WHERE
            budget_module = '{module}'
        """,
    )

    remaining_audit = scalar_count(
        client,
        f"""
        SELECT COUNT(*) AS total
        FROM `{audit_table}` AS audit
        WHERE EXISTS (
            SELECT 1
            FROM `{batch_table}` AS batch
            WHERE
                batch.batch_id
                    = audit.batch_id
                AND batch.budget_module
                    = '{module}'
        )
        """,
    )

    print()
    print("=" * 86)
    print("RESULTADO")
    print("=" * 86)

    print(
        f"CAPEX principal : "
        f"{remaining_main:,}"
    )

    print(
        f"CAPEX batches   : "
        f"{remaining_batches:,}"
    )

    print(
        f"CAPEX auditoria : "
        f"{remaining_audit:,}"
    )

    if (
        remaining_main != 0
        or remaining_batches != 0
        or remaining_audit != 0
    ):
        raise RuntimeError(
            "El reset termino, pero "
            "la validacion no quedo en cero."
        )

    print()
    print(
        "[OK] CAPEX listo para "
        "carga real 2027."
    )

    print()
    print(
        "SharePoint NO fue modificado."
    )

    print(
        "OPEX NO fue modificado."
    )

    print()
    print(
        "Backups temporales:"
    )

    print(
        f"  {backup_main}"
    )

    print(
        f"  {backup_batches}"
    )

    print(
        f"  {backup_audit}"
    )

    print(
        f"  {backup_staging}"
    )


if __name__ == "__main__":
    main()
