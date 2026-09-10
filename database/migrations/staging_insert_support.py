
from dataclasses import dataclass


OPERATION_COLUMN = (
    "operation"
)

PAYLOAD_COLUMN = (
    "insert_payload"
)

COLUMNS = (
    OPERATION_COLUMN,
    PAYLOAD_COLUMN,
)


class StagingInsertMigrationError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class StagingInsertMigrationResult:
    table_id: str
    status: str
    existing_columns: tuple[
        str,
        ...
    ]
    added_columns: tuple[
        str,
        ...
    ]


def _required_text(
    value,
    field_name,
):
    text = str(
        value
        if value is not None
        else ""
    ).strip()

    if not text:
        raise StagingInsertMigrationError(
            f"{field_name} no puede "
            "estar vacio."
        )

    return text


def _schema_map(
    table,
):
    return {
        field.name:
            field
        for field in table.schema
    }


def _validate_field(
    field,
    column,
):
    if (
        str(
            field.field_type
        )
        .strip()
        .upper()
        != "STRING"
    ):
        raise StagingInsertMigrationError(
            f"{column} existe pero "
            "no es STRING."
        )

    if (
        str(
            field.mode
        )
        .strip()
        .upper()
        != "NULLABLE"
    ):
        raise StagingInsertMigrationError(
            f"{column} existe pero "
            "no es NULLABLE."
        )


def migrate_staging_insert_support(
    client,
    *,
    project,
    dataset,
    staging_table,
    location,
    apply=False,
):
    project_value = _required_text(
        project,
        "project",
    )

    dataset_value = _required_text(
        dataset,
        "dataset",
    )

    table_value = _required_text(
        staging_table,
        "staging_table",
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
        raise StagingInsertMigrationError(
            "No se pudo leer la tabla "
            f"{table_id}."
        ) from exc

    schema = _schema_map(
        table
    )

    existing = []

    missing = []

    for column in COLUMNS:
        field = schema.get(
            column
        )

        if field is None:
            missing.append(
                column
            )
            continue

        _validate_field(
            field,
            column,
        )

        existing.append(
            column
        )

    if not apply:
        return (
            StagingInsertMigrationResult(
                table_id=table_id,
                status=(
                    "EXISTS"
                    if not missing
                    else "WOULD_ADD"
                ),
                existing_columns=tuple(
                    existing
                ),
                added_columns=tuple(
                    missing
                ),
            )
        )

    for column in missing:
        sql = f"""
            ALTER TABLE `{table_id}`
            ADD COLUMN IF NOT EXISTS
                `{column}` STRING
        """

        client.query(
            sql,
            location=location_value,
        ).result()

    try:
        final_table = client.get_table(
            table_id
        )

    except Exception as exc:
        raise StagingInsertMigrationError(
            "No se pudo validar la tabla "
            "despues de la migracion."
        ) from exc

    final_schema = _schema_map(
        final_table
    )

    for column in COLUMNS:
        field = final_schema.get(
            column
        )

        if field is None:
            raise StagingInsertMigrationError(
                "La migracion no creo "
                f"{column}."
            )

        _validate_field(
            field,
            column,
        )

    return StagingInsertMigrationResult(
        table_id=table_id,
        status=(
            "EXISTS"
            if not missing
            else "MIGRATED"
        ),
        existing_columns=tuple(
            existing
        ),
        added_columns=tuple(
            missing
        ),
    )
