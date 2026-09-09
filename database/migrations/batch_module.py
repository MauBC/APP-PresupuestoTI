from dataclasses import dataclass


BUDGET_MODULE_COLUMN = "budget_module"
DEFAULT_HISTORICAL_MODULE = "OPEX"

VALID_MODULES = (
    "OPEX",
    "CAPEX",
)


class BatchModuleMigrationError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class BatchModuleMigrationResult:
    table_id: str
    status: str
    column_existed: bool
    updated_rows: int


def _required_text(
    value,
    field_name: str,
) -> str:
    text = str(
        value
        if value is not None
        else ""
    ).strip()

    if not text:
        raise BatchModuleMigrationError(
            f"{field_name} no puede estar vacio."
        )

    return text


def _find_column(
    table,
    column_name: str,
):
    for field in table.schema:
        if field.name == column_name:
            return field

    return None


def _validate_existing_column(
    field,
) -> None:
    if (
        str(field.field_type)
        .strip()
        .upper()
        != "STRING"
    ):
        raise BatchModuleMigrationError(
            "budget_module existe pero "
            "no es STRING."
        )

    if (
        str(field.mode)
        .strip()
        .upper()
        != "NULLABLE"
    ):
        raise BatchModuleMigrationError(
            "budget_module existe pero "
            "no es NULLABLE."
        )


def migrate_batch_module(
    client,
    *,
    project: str,
    dataset: str,
    batch_table: str,
    location: str,
    apply: bool = False,
) -> BatchModuleMigrationResult:
    project_value = _required_text(
        project,
        "project",
    )

    dataset_value = _required_text(
        dataset,
        "dataset",
    )

    table_value = _required_text(
        batch_table,
        "batch_table",
    )

    location_value = _required_text(
        location,
        "location",
    )

    table_id = (
        f"{project_value}."
        f"{dataset_value}."
        f"{table_value}"
    )

    try:
        table = client.get_table(
            table_id
        )

    except Exception as exc:
        raise BatchModuleMigrationError(
            "No se pudo leer la tabla "
            f"{table_id}."
        ) from exc

    existing_field = _find_column(
        table,
        BUDGET_MODULE_COLUMN,
    )

    column_existed = (
        existing_field is not None
    )

    if existing_field is not None:
        _validate_existing_column(
            existing_field
        )

    if not apply:
        return BatchModuleMigrationResult(
            table_id=table_id,
            status=(
                "EXISTS"
                if column_existed
                else "WOULD_ADD"
            ),
            column_existed=(
                column_existed
            ),
            updated_rows=0,
        )

    if not column_existed:
        alter_sql = f"""
            ALTER TABLE `{table_id}`
            ADD COLUMN IF NOT EXISTS
                `{BUDGET_MODULE_COLUMN}` STRING
        """

        client.query(
            alter_sql,
            location=location_value,
        ).result()

    update_sql = f"""
        UPDATE `{table_id}`
        SET
            `{BUDGET_MODULE_COLUMN}`
            = @default_module
        WHERE
            `{BUDGET_MODULE_COLUMN}` IS NULL
            OR TRIM(
                `{BUDGET_MODULE_COLUMN}`
            ) = ''
    """

    from google.cloud import bigquery

    update_config = (
        bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "default_module",
                    "STRING",
                    DEFAULT_HISTORICAL_MODULE,
                )
            ]
        )
    )

    update_job = client.query(
        update_sql,
        job_config=update_config,
        location=location_value,
    )

    update_job.result()

    updated_rows = int(
        getattr(
            update_job,
            "num_dml_affected_rows",
            0,
        )
        or 0
    )

    validation_sql = f"""
        SELECT
            COUNTIF(
                `{BUDGET_MODULE_COLUMN}`
                IS NULL
                OR TRIM(
                    `{BUDGET_MODULE_COLUMN}`
                ) = ''
            ) AS missing_rows,

            COUNTIF(
                `{BUDGET_MODULE_COLUMN}`
                IS NOT NULL
                AND TRIM(
                    `{BUDGET_MODULE_COLUMN}`
                ) != ''
                AND UPPER(
                    TRIM(
                        `{BUDGET_MODULE_COLUMN}`
                    )
                ) NOT IN (
                    'OPEX',
                    'CAPEX'
                )
            ) AS invalid_rows

        FROM `{table_id}`
    """

    validation_rows = list(
        client.query(
            validation_sql,
            location=location_value,
        ).result()
    )

    if len(validation_rows) != 1:
        raise BatchModuleMigrationError(
            "No se pudo validar "
            "budget_module."
        )

    validation = (
        validation_rows[0]
    )

    try:
        missing_rows = int(
            validation[
                "missing_rows"
            ]
            or 0
        )

        invalid_rows = int(
            validation[
                "invalid_rows"
            ]
            or 0
        )

    except (
        KeyError,
        TypeError,
    ):
        missing_rows = int(
            getattr(
                validation,
                "missing_rows",
                0,
            )
            or 0
        )

        invalid_rows = int(
            getattr(
                validation,
                "invalid_rows",
                0,
            )
            or 0
        )

    if missing_rows:
        raise BatchModuleMigrationError(
            "Quedaron batches sin "
            "budget_module."
        )

    if invalid_rows:
        raise BatchModuleMigrationError(
            "Existen valores no reconocidos "
            "en budget_module."
        )

    return BatchModuleMigrationResult(
        table_id=table_id,
        status="MIGRATED",
        column_existed=(
            column_existed
        ),
        updated_rows=updated_rows,
    )
