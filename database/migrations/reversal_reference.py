from dataclasses import dataclass


COLUMN_NAME = (
    "reverted_batch_id"
)


class ReversalReferenceMigrationError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class ReversalReferenceMigrationResult:
    table_id: str
    status: str
    column_existed: bool


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
        raise ReversalReferenceMigrationError(
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


def _validate_existing(
    field,
):
    if (
        str(field.field_type)
        .strip()
        .upper()
        != "STRING"
    ):
        raise ReversalReferenceMigrationError(
            "reverted_batch_id existe pero "
            "no es STRING."
        )

    if (
        str(field.mode)
        .strip()
        .upper()
        != "NULLABLE"
    ):
        raise ReversalReferenceMigrationError(
            "reverted_batch_id existe pero "
            "no es NULLABLE."
        )


def migrate_reversal_reference(
    client,
    *,
    project: str,
    dataset: str,
    batch_table: str,
    location: str,
    apply: bool = False,
) -> ReversalReferenceMigrationResult:
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
        raise ReversalReferenceMigrationError(
            "No se pudo leer la tabla "
            f"{table_id}."
        ) from exc

    field = _find_column(
        table
    )

    existed = (
        field is not None
    )

    if field is not None:
        _validate_existing(
            field
        )

    if not apply:
        return ReversalReferenceMigrationResult(
            table_id=table_id,
            status=(
                "EXISTS"
                if existed
                else "WOULD_ADD"
            ),
            column_existed=existed,
        )

    if not existed:
        sql = f"""
            ALTER TABLE `{table_id}`
            ADD COLUMN IF NOT EXISTS
                `{COLUMN_NAME}` STRING
        """

        client.query(
            sql,
            location=location_value,
        ).result()

    table_after = client.get_table(
        table_id
    )

    field_after = _find_column(
        table_after
    )

    if field_after is None:
        raise ReversalReferenceMigrationError(
            "La columna reverted_batch_id "
            "no existe despues de migrar."
        )

    _validate_existing(
        field_after
    )

    return ReversalReferenceMigrationResult(
        table_id=table_id,
        status="MIGRATED",
        column_existed=existed,
    )
