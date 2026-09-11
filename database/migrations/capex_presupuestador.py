from dataclasses import dataclass


COLUMN_NAME = "presupuestador"
COLUMN_TYPE = "STRING"
COLUMN_MODE = "NULLABLE"


class CapexPresupuestadorMigrationError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class CapexPresupuestadorMigrationResult:
    table_id: str
    status: str
    column_existed: bool


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
        raise CapexPresupuestadorMigrationError(
            f"{field_name} no puede estar vacio."
        )

    return text


def _find_column(
    table,
):
    for field in table.schema:
        if field.name == COLUMN_NAME:
            return field

    return None


def _validate_column(
    field,
):
    if (
        str(field.field_type)
        .strip()
        .upper()
        != COLUMN_TYPE
    ):
        raise CapexPresupuestadorMigrationError(
            "presupuestador existe pero "
            "no es STRING."
        )

    if (
        str(field.mode)
        .strip()
        .upper()
        != COLUMN_MODE
    ):
        raise CapexPresupuestadorMigrationError(
            "presupuestador existe pero "
            "no es NULLABLE."
        )


def migrate_capex_presupuestador(
    client,
    *,
    project,
    dataset,
    table,
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
        table,
        "table",
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
        remote_table = client.get_table(
            table_id
        )

    except Exception as exc:
        raise CapexPresupuestadorMigrationError(
            "No se pudo leer la tabla "
            f"{table_id}."
        ) from exc

    existing = _find_column(
        remote_table
    )

    column_existed = (
        existing is not None
    )

    if existing is not None:
        _validate_column(
            existing
        )

    if not apply:
        return (
            CapexPresupuestadorMigrationResult(
                table_id=table_id,
                status=(
                    "EXISTS"
                    if column_existed
                    else "WOULD_ADD"
                ),
                column_existed=(
                    column_existed
                ),
            )
        )

    if not column_existed:
        sql = f"""
            ALTER TABLE `{table_id}`
            ADD COLUMN IF NOT EXISTS
                `{COLUMN_NAME}` STRING
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
        raise CapexPresupuestadorMigrationError(
            "No se pudo validar la tabla "
            "despues de la migracion."
        ) from exc

    final_field = _find_column(
        final_table
    )

    if final_field is None:
        raise CapexPresupuestadorMigrationError(
            "La migracion no creo "
            "presupuestador."
        )

    _validate_column(
        final_field
    )

    return CapexPresupuestadorMigrationResult(
        table_id=table_id,
        status=(
            "EXISTS"
            if column_existed
            else "MIGRATED"
        ),
        column_existed=(
            column_existed
        ),
    )
