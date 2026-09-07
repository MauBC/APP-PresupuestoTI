from datetime import (
    datetime,
    timezone,
)

from database.persistence.contract import (
    EDITABLE_COLUMNS,
    PENDING_STATUS,
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
            )
        )

    return tuple(result)
