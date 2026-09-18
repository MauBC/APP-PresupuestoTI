
import json
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

from database.persistence.contract import (
    EDITABLE_COLUMNS,
    INSERT_OPERATION,
    PENDING_STATUS,
    UPDATE_OPERATION,
)
from database.persistence.models import (
    PersistenceBatch,
    StagingRow,
)


class StagingBuildError(
    ValueError
):
    pass


def _normalize_timestamp(
    value: datetime,
) -> datetime:
    if not isinstance(
        value,
        datetime,
    ):
        raise StagingBuildError(
            "staged_at debe ser datetime."
        )

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise StagingBuildError(
            "staged_at debe incluir "
            "zona horaria."
        )

    return value.astimezone(
        timezone.utc
    )


def _json_default(
    value,
):
    if isinstance(
        value,
        Decimal,
    ):
        return format(
            value,
            "f",
        )

    if isinstance(
        value,
        datetime,
    ):
        return (
            value
            .astimezone(
                timezone.utc
            )
            .isoformat()
        )

    raise TypeError(
        "Valor no serializable "
        "en insert_payload: "
        f"{type(value).__name__}"
    )


def _insert_payload(
    row,
) -> str | None:
    if not row.insert_values:
        return None

    return json.dumps(
        dict(row.insert_values),
        ensure_ascii=False,
        separators=(",", ":"),
        default=_json_default,
    )
def build_staging_rows(
    batch: PersistenceBatch,
    *,
    timestamp: datetime | None = None,
) -> tuple[
    StagingRow,
    ...
]:
    if batch.status != PENDING_STATUS:
        raise StagingBuildError(
            "Solo un batch PENDING puede "
            "prepararse para staging."
        )

    if not batch.rows:
        raise StagingBuildError(
            "El batch no contiene filas."
        )

    effective_timestamp = (
        timestamp
        if timestamp is not None
        else batch.created_at
    )

    staged_at = (
        _normalize_timestamp(
            effective_timestamp
        )
    )

    result = []

    for row in batch.rows:
        columns = tuple(
            column
            for column, _
            in row.editable_values
        )

        if columns != EDITABLE_COLUMNS:
            raise StagingBuildError(
                "Las columnas editables de "
                "la fila no coinciden con "
                "el contrato de staging."
            )

        operation = (
            str(
                row.operation
            )
            .strip()
            .upper()
        )

        if operation not in {
            UPDATE_OPERATION,
            INSERT_OPERATION,
        }:
            raise StagingBuildError(
                "Operacion de persistencia "
                "no soportada: "
                f"{row.operation}"
            )

        if (
            operation
            == UPDATE_OPERATION
            and row.expected_version < 1
        ):
            raise StagingBuildError(
                "UPDATE requiere "
                "expected_version >= 1."
            )

        if (
            operation
            == INSERT_OPERATION
            and row.expected_version != 0
        ):
            raise StagingBuildError(
                "INSERT requiere "
                "expected_version = 0."
            )

        result.append(
            StagingRow(
                batch_id=batch.batch_id,
                row_id=row.row_id,
                expected_version=(
                    row.expected_version
                ),
                editable_values=(
                    row.editable_values
                ),
                staged_at=staged_at,
                operation=operation,
                insert_payload=(
                    _insert_payload(
                        row
                    )
                ),
                insert_values=(
                    row.insert_values
                ),
            )
        )

    return tuple(result)
