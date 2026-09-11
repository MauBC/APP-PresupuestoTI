
from datetime import (
    datetime,
    timezone,
)
from decimal import (
    Decimal,
    InvalidOperation,
)
from uuid import uuid4

from database.persistence.contract import (
    EDITABLE_VALUE_TYPES,
)
from database.persistence.models import (
    AuditChange,
    PersistenceBatch,
)


class AuditBuildError(
    ValueError
):
    pass


SUPPORTED_VALUE_TYPES = {
    "BOOLEAN",
    "NUMERIC",
    "STRING",
    "INTEGER",
}


def generate_audit_id() -> str:
    return str(
        uuid4()
    )


def _normalize_timestamp(
    value: datetime,
) -> datetime:
    if not isinstance(
        value,
        datetime,
    ):
        raise AuditBuildError(
            "changed_at debe ser datetime."
        )

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise AuditBuildError(
            "changed_at debe incluir "
            "zona horaria."
        )

    return value.astimezone(
        timezone.utc
    )


def _serialize_boolean(
    value,
) -> str:
    if not isinstance(
        value,
        bool,
    ):
        raise AuditBuildError(
            "El valor BOOLEAN de auditoria "
            "debe ser bool."
        )

    return (
        "true"
        if value
        else "false"
    )


def _serialize_numeric(
    value,
) -> str:
    if isinstance(
        value,
        bool,
    ):
        raise AuditBuildError(
            "Un valor BOOLEAN no puede "
            "auditarse como NUMERIC."
        )

    try:
        decimal_value = (
            value
            if isinstance(
                value,
                Decimal,
            )
            else Decimal(
                str(value)
            )
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ) as exc:
        raise AuditBuildError(
            "Valor NUMERIC no valido "
            "para auditoria."
        ) from exc

    if not decimal_value.is_finite():
        raise AuditBuildError(
            "El valor NUMERIC de auditoria "
            "debe ser finito."
        )

    return format(
        decimal_value,
        "f",
    )


def _serialize_integer(
    value,
) -> str:
    if isinstance(
        value,
        bool,
    ):
        raise AuditBuildError(
            "BOOLEAN no puede auditarse "
            "como INTEGER."
        )

    try:
        integer_value = int(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise AuditBuildError(
            "Valor INTEGER no valido "
            "para auditoria."
        ) from exc

    if str(
        value
    ).strip() not in {
        str(integer_value),
        f"+{integer_value}",
    } and not isinstance(
        value,
        int,
    ):
        raise AuditBuildError(
            "Valor INTEGER no valido "
            "para auditoria."
        )

    return str(
        integer_value
    )


def serialize_audit_value(
    value,
    value_type: str,
) -> str | None:
    if value is None:
        return None

    if value_type == "BOOLEAN":
        return _serialize_boolean(
            value
        )

    if value_type == "NUMERIC":
        return _serialize_numeric(
            value
        )

    if value_type == "STRING":
        return str(
            value
        )

    if value_type == "INTEGER":
        return _serialize_integer(
            value
        )

    raise AuditBuildError(
        "Tipo de auditoria no soportado: "
        f"{value_type}"
    )


def build_audit_changes(
    batch: PersistenceBatch,
    *,
    timestamp: datetime | None = None,
    audit_id_factory=generate_audit_id,
) -> tuple[
    AuditChange,
    ...
]:
    changed_at = (
        timestamp
        if timestamp is not None
        else batch.created_at
    )

    changed_at = (
        _normalize_timestamp(
            changed_at
        )
    )

    result = []

    seen_audit_ids = set()

    for row in batch.rows:
        insert_columns = set(
            row.insert_dict()
        )

        for field_change in (
            row.field_changes
        ):
            if row.is_update:
                expected_type = (
                    EDITABLE_VALUE_TYPES.get(
                        field_change.column
                    )
                )

                if (
                    expected_type is None
                    and field_change.column in insert_columns
                    and field_change.value_type in SUPPORTED_VALUE_TYPES
                ):
                    expected_type = field_change.value_type

                if expected_type is None:
                    raise AuditBuildError(
                        "Columna no soportada "
                        "para auditoria: "
                        f"{field_change.column}"
                    )

                if (
                    field_change.value_type
                    != expected_type
                ):
                    raise AuditBuildError(
                        "El tipo de auditoria "
                        "no coincide con el "
                        "contrato para "
                        f"{field_change.column}."
                    )

            else:
                if (
                    field_change.value_type
                    not in SUPPORTED_VALUE_TYPES
                ):
                    raise AuditBuildError(
                        "Tipo INSERT no soportado "
                        "para auditoria: "
                        f"{field_change.value_type}"
                    )

                if (
                    field_change.column
                    != "habilitado"
                    and field_change.column
                    not in insert_columns
                ):
                    raise AuditBuildError(
                        "La auditoria INSERT "
                        "contiene una columna "
                        "fuera del payload."
                    )

            audit_id = str(
                audit_id_factory()
            ).strip()

            if not audit_id:
                raise AuditBuildError(
                    "audit_id no puede "
                    "estar vacio."
                )

            if (
                audit_id
                in seen_audit_ids
            ):
                raise AuditBuildError(
                    "Se generaron audit_id "
                    "duplicados."
                )

            seen_audit_ids.add(
                audit_id
            )

            result.append(
                AuditChange(
                    audit_id=audit_id,
                    batch_id=(
                        batch.batch_id
                    ),
                    row_id=row.row_id,
                    column_name=(
                        field_change.column
                    ),
                    value_type=(
                        field_change.value_type
                    ),
                    before_value=(
                        serialize_audit_value(
                            field_change.before,
                            field_change.value_type,
                        )
                    ),
                    after_value=(
                        serialize_audit_value(
                            field_change.after,
                            field_change.value_type,
                        )
                    ),
                    version_before=(
                        row.expected_version
                    ),
                    version_after=(
                        row.version_after
                    ),
                    actor=batch.actor,
                    changed_at=(
                        changed_at
                    ),
                )
            )

    if (
        len(result)
        != batch.field_count
    ):
        raise AuditBuildError(
            "La cantidad de registros "
            "de auditoria no coincide con "
            "field_count."
        )

    return tuple(result)
