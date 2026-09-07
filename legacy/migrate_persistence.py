import argparse
from datetime import (
    datetime,
    timezone,
)

from google.api_core.exceptions import (
    NotFound,
)

from app.config.presupuesto_app_config import (
    DIMENSION_COLUMNS,
    USD_COLUMNS,
)
from app.config.presupuesto_schema import (
    EXPECTED_TYPES,
    LEGACY_EXPECTED_TYPES,
    PERSISTENCE_TYPES,
)
from app.config.settings import settings
from app.services.bigquery_service import (
    BigQueryService,
)


CONFIRMATION_TEXT = "MIGRAR_PERSISTENCIA"


def get_table_ref(
    table_name: str,
) -> str:
    project = settings.GOOGLE_CLOUD_PROJECT
    dataset = settings.BIGQUERY_DATASET

    if not project or not dataset:
        raise ValueError(
            "Proyecto o dataset no configurado."
        )

    return (
        f"{project}.{dataset}.{table_name}"
    )


def run_query(
    service,
    sql,
):
    return (
        service.client
        .query(
            sql,
            location=(
                settings.BIGQUERY_LOCATION
            ),
        )
        .result()
    )


def table_exists(
    service,
    table_ref,
):
    try:
        service.client.get_table(
            table_ref
        )
        return True

    except NotFound:
        return False


def inspect_main_table(
    service,
):
    table = service.get_table()

    actual_types = {
        field.name: field.field_type
        for field in table.schema
    }

    wrong_legacy = {
        column: {
            "expected": expected,
            "actual": actual_types.get(
                column
            ),
        }
        for column, expected
        in LEGACY_EXPECTED_TYPES.items()
        if actual_types.get(column)
        != expected
    }

    unexpected = (
        set(actual_types)
        - set(EXPECTED_TYPES)
    )

    wrong_persistence = {
        column: {
            "expected": expected,
            "actual": actual_types.get(
                column
            ),
        }
        for column, expected
        in PERSISTENCE_TYPES.items()
        if (
            column in actual_types
            and actual_types[column]
            != expected
        )
    }

    missing_persistence = [
        column
        for column in PERSISTENCE_TYPES
        if column not in actual_types
    ]

    return {
        "table": table,
        "actual_types": actual_types,
        "wrong_legacy": wrong_legacy,
        "wrong_persistence": (
            wrong_persistence
        ),
        "unexpected": unexpected,
        "missing_persistence": (
            missing_persistence
        ),
    }


def validate_preconditions(
    state,
):
    errors = []

    if state["wrong_legacy"]:
        errors.append(
            "Tipos legacy incorrectos: "
            + str(
                state["wrong_legacy"]
            )
        )

    if state["wrong_persistence"]:
        errors.append(
            "Tipos tecnicos incorrectos: "
            + str(
                state["wrong_persistence"]
            )
        )

    if state["unexpected"]:
        errors.append(
            "Columnas inesperadas: "
            + str(
                sorted(
                    state["unexpected"]
                )
            )
        )

    if errors:
        raise RuntimeError(
            "\n".join(errors)
        )


def create_snapshot(
    service,
):
    source = (
        service.get_table_reference()
    )

    timestamp = (
        datetime.now(timezone.utc)
        .strftime("%Y%m%d_%H%M%S")
    )

    snapshot_name = (
        f"{settings.BIGQUERY_TABLE}"
        f"_pre_persistencia_"
        f"{timestamp}"
    )

    snapshot_ref = get_table_ref(
        snapshot_name
    )

    sql = f"""
        CREATE SNAPSHOT TABLE
        `{snapshot_ref}`
        CLONE `{source}`
    """

    run_query(
        service,
        sql,
    )

    return snapshot_ref


def add_persistence_columns(
    service,
):
    table_ref = (
        service.get_table_reference()
    )

    definitions = (
        (
            "row_id",
            "STRING",
            "GENERATE_UUID()",
        ),
        (
            "habilitado",
            "BOOL",
            "TRUE",
        ),
        (
            "version",
            "INT64",
            "1",
        ),
        (
            "created_at",
            "TIMESTAMP",
            "CURRENT_TIMESTAMP()",
        ),
        (
            "created_by",
            "STRING",
            "SESSION_USER()",
        ),
        (
            "updated_at",
            "TIMESTAMP",
            "CURRENT_TIMESTAMP()",
        ),
        (
            "updated_by",
            "STRING",
            "SESSION_USER()",
        ),
    )

    for (
        column,
        column_type,
        default_expression,
    ) in definitions:
        add_sql = f"""
            ALTER TABLE `{table_ref}`
            ADD COLUMN IF NOT EXISTS
            `{column}` {column_type}
        """

        run_query(
            service,
            add_sql,
        )

        default_sql = f"""
            ALTER TABLE `{table_ref}`
            ALTER COLUMN `{column}`
            SET DEFAULT {default_expression}
        """

        run_query(
            service,
            default_sql,
        )


def backfill_persistence(
    service,
):
    table_ref = (
        service.get_table_reference()
    )

    sql = f"""
        UPDATE `{table_ref}`
        SET
            row_id = COALESCE(
                row_id,
                GENERATE_UUID()
            ),
            habilitado = COALESCE(
                habilitado,
                TRUE
            ),
            version = COALESCE(
                version,
                1
            ),
            created_at = COALESCE(
                created_at,
                CURRENT_TIMESTAMP()
            ),
            created_by = COALESCE(
                created_by,
                'MIGRATION_LEGACY'
            ),
            updated_at = COALESCE(
                updated_at,
                CURRENT_TIMESTAMP()
            ),
            updated_by = COALESCE(
                updated_by,
                'MIGRATION_LEGACY'
            )
        WHERE
            row_id IS NULL
            OR habilitado IS NULL
            OR version IS NULL
            OR created_at IS NULL
            OR created_by IS NULL
            OR updated_at IS NULL
            OR updated_by IS NULL
    """

    run_query(
        service,
        sql,
    )


def create_batch_table(
    service,
):
    table_ref = get_table_ref(
        settings.BIGQUERY_BATCH_TABLE
    )

    sql = f"""
        CREATE TABLE IF NOT EXISTS
        `{table_ref}` (
            batch_id STRING NOT NULL
                DEFAULT GENERATE_UUID(),

            changed_at TIMESTAMP NOT NULL
                DEFAULT CURRENT_TIMESTAMP(),

            changed_by STRING NOT NULL
                DEFAULT SESSION_USER(),

            app_version STRING NOT NULL,
            status STRING NOT NULL,

            affected_rows INT64 NOT NULL,
            affected_fields INT64 NOT NULL,

            original_total_usd NUMERIC NOT NULL,
            new_total_usd NUMERIC NOT NULL,
            delta_usd NUMERIC NOT NULL,

            comment STRING,
            error_message STRING
        )
        PARTITION BY DATE(changed_at)
        CLUSTER BY status, changed_by
        OPTIONS (
            description = (
                'Cabecera de cada lote de '
                'cambios aplicado por '
                'APP Presupuesto TI'
            )
        )
    """

    run_query(
        service,
        sql,
    )


def create_audit_table(
    service,
):
    table_ref = get_table_ref(
        settings.BIGQUERY_AUDIT_TABLE
    )

    sql = f"""
        CREATE TABLE IF NOT EXISTS
        `{table_ref}` (
            audit_id STRING NOT NULL
                DEFAULT GENERATE_UUID(),

            batch_id STRING NOT NULL,
            row_id STRING NOT NULL,

            action STRING NOT NULL,

            changed_at TIMESTAMP NOT NULL
                DEFAULT CURRENT_TIMESTAMP(),

            changed_by STRING NOT NULL
                DEFAULT SESSION_USER(),

            app_version STRING NOT NULL,

            original_version INT64,
            new_version INT64,

            changed_columns ARRAY<STRING>,

            before_json JSON,
            after_json JSON
        )
        PARTITION BY DATE(changed_at)
        CLUSTER BY batch_id, row_id, changed_by
        OPTIONS (
            description = (
                'Auditoria detallada por fila '
                'de APP Presupuesto TI'
            )
        )
    """

    run_query(
        service,
        sql,
    )


def create_staging_table(
    service,
):
    table_ref = get_table_ref(
        settings.BIGQUERY_STAGING_TABLE
    )

    dimension_definitions = ",\n".join(
        f"`{column}` STRING"
        for column in DIMENSION_COLUMNS
    )

    usd_definitions = ",\n".join(
        f"`{column}` NUMERIC"
        for column in USD_COLUMNS
    )

    sql = f"""
        CREATE TABLE IF NOT EXISTS
        `{table_ref}` (
            batch_id STRING NOT NULL,
            operation STRING NOT NULL,

            staged_at TIMESTAMP NOT NULL
                DEFAULT CURRENT_TIMESTAMP(),

            row_id STRING NOT NULL,
            original_version INT64,

            {dimension_definitions},

            habilitado BOOL,

            {usd_definitions}
        )
        PARTITION BY DATE(staged_at)
        CLUSTER BY batch_id, operation
        OPTIONS (
            partition_expiration_days = 7,
            description = (
                'Staging temporal para lotes '
                'de APP Presupuesto TI'
            )
        )
    """

    run_query(
        service,
        sql,
    )


def validate_main_data(
    service,
):
    table_ref = (
        service.get_table_reference()
    )

    sql = f"""
        SELECT
            COUNT(*) AS total_rows,

            COUNT(row_id)
                AS row_id_not_null,

            COUNT(DISTINCT row_id)
                AS distinct_row_id,

            COUNTIF(row_id IS NULL)
                AS null_row_id,

            COUNTIF(habilitado IS NULL)
                AS null_habilitado,

            COUNTIF(version IS NULL)
                AS null_version,

            COUNTIF(version < 1)
                AS invalid_version,

            COUNTIF(created_at IS NULL)
                AS null_created_at,

            COUNTIF(created_by IS NULL)
                AS null_created_by,

            COUNTIF(updated_at IS NULL)
                AS null_updated_at,

            COUNTIF(updated_by IS NULL)
                AS null_updated_by

        FROM `{table_ref}`
    """

    result = next(
        iter(
            run_query(
                service,
                sql,
            )
        )
    )

    data = dict(
        result.items()
    )

    total = data[
        "total_rows"
    ]

    errors = []

    if (
        data["row_id_not_null"]
        != total
    ):
        errors.append(
            "Existen row_id nulos."
        )

    if (
        data["distinct_row_id"]
        != total
    ):
        errors.append(
            "Existen row_id duplicados."
        )

    for key in (
        "null_row_id",
        "null_habilitado",
        "null_version",
        "invalid_version",
        "null_created_at",
        "null_created_by",
        "null_updated_at",
        "null_updated_by",
    ):
        if data[key] != 0:
            errors.append(
                f"{key} = {data[key]}"
            )

    if errors:
        raise RuntimeError(
            "Validacion fallida:\n"
            + "\n".join(errors)
        )

    return data


def print_state(
    service,
):
    state = inspect_main_table(
        service
    )

    validate_preconditions(
        state
    )

    table = state["table"]

    print("")
    print("=== ESTADO PERSISTENCIA ===")
    print(
        "Tabla principal : "
        f"{table.full_table_id}"
    )
    print(
        "Filas           : "
        f"{table.num_rows:,}"
    )
    print(
        "Columnas        : "
        f"{len(table.schema)}"
    )

    if state[
        "missing_persistence"
    ]:
        print(
            "Faltan tecnicas : "
            + ", ".join(
                state[
                    "missing_persistence"
                ]
            )
        )
    else:
        print(
            "Columnas tecnicas: OK"
        )

        validation = (
            validate_main_data(
                service
            )
        )

        print(
            "row_id unicos   : "
            f"{validation['distinct_row_id']:,}"
        )

    for table_name, label in (
        (
            settings.BIGQUERY_BATCH_TABLE,
            "Batches",
        ),
        (
            settings.BIGQUERY_AUDIT_TABLE,
            "Audit",
        ),
        (
            settings.BIGQUERY_STAGING_TABLE,
            "Staging",
        ),
    ):
        ref = get_table_ref(
            table_name
        )

        status = (
            "OK"
            if table_exists(
                service,
                ref,
            )
            else "NO EXISTE"
        )

        print(
            f"{label:<15}: {status}"
        )

    print("")


def apply_migration(
    service,
):
    state = inspect_main_table(
        service
    )

    validate_preconditions(
        state
    )

    print(
        "Creando snapshot de respaldo..."
    )

    snapshot_ref = create_snapshot(
        service
    )

    print(
        "Snapshot creado:"
    )
    print(
        f"  {snapshot_ref}"
    )

    print(
        "Agregando columnas tecnicas..."
    )

    add_persistence_columns(
        service
    )

    print(
        "Completando datos legacy..."
    )

    backfill_persistence(
        service
    )

    print(
        "Creando tabla de batches..."
    )

    create_batch_table(
        service
    )

    print(
        "Creando tabla de auditoria..."
    )

    create_audit_table(
        service
    )

    print(
        "Creando tabla staging..."
    )

    create_staging_table(
        service
    )

    print(
        "Validando tabla principal..."
    )

    result = validate_main_data(
        service
    )

    print("")
    print(
        "MIGRACION COMPLETADA"
    )
    print(
        "Filas               : "
        f"{result['total_rows']:,}"
    )
    print(
        "row_id no nulos      : "
        f"{result['row_id_not_null']:,}"
    )
    print(
        "row_id distintos     : "
        f"{result['distinct_row_id']:,}"
    )
    print(
        "row_id duplicados    : "
        f"{result['total_rows'] - result['distinct_row_id']:,}"
    )
    print("")
    print(
        "BigQuery preparado para "
        "persistencia controlada."
    )
    print("")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Migracion de persistencia "
            "APP Presupuesto TI"
        )
    )

    subparsers = (
        parser.add_subparsers(
            dest="command",
            required=True,
        )
    )

    subparsers.add_parser(
        "check",
        help=(
            "Inspecciona el estado "
            "sin modificar BigQuery."
        ),
    )

    apply_parser = (
        subparsers.add_parser(
            "apply",
            help=(
                "Crea snapshot y aplica "
                "la migracion."
            ),
        )
    )

    apply_parser.add_argument(
        "--confirm",
        required=True,
    )

    args = parser.parse_args()

    service = BigQueryService()

    if args.command == "check":
        print_state(
            service
        )
        return

    if (
        args.confirm
        != CONFIRMATION_TEXT
    ):
        raise ValueError(
            "Confirmacion incorrecta. "
            "Use --confirm "
            f"{CONFIRMATION_TEXT}"
        )

    apply_migration(
        service
    )


if __name__ == "__main__":
    main()