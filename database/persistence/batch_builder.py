from copy import deepcopy
from datetime import (
    datetime,
    timezone,
)
from uuid import uuid4

from app.config.presupuesto_app_config import (
    ROW_ID_COLUMN,
    VERSION_COLUMN,
)
from database.persistence.contract import (
    EDITABLE_COLUMNS,
    EDITABLE_VALUE_TYPES,
    PENDING_STATUS,
)
from database.persistence.models import (
    PersistenceBatch,
    PersistenceFieldChange,
    PersistenceRowChange,
)


class PersistenceBuildError(
    ValueError
):
    pass


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def generate_batch_id() -> str:
    return str(
        uuid4()
    )


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
        raise PersistenceBuildError(
            f"{field_name} no puede estar vacio."
        )

    return text


def _normalize_timestamp(
    value: datetime,
) -> datetime:
    if not isinstance(
        value,
        datetime,
    ):
        raise PersistenceBuildError(
            "created_at debe ser datetime."
        )

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise PersistenceBuildError(
            "created_at debe incluir "
            "zona horaria."
        )

    return value.astimezone(
        timezone.utc
    )


def _required_version(
    value,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
    ):
        raise PersistenceBuildError(
            "version debe ser un entero."
        )

    if value < 1:
        raise PersistenceBuildError(
            "version debe ser mayor "
            "o igual a 1."
        )

    return value


def _build_row_change(
    workspace,
    pending_change,
) -> PersistenceRowChange:
    session_row_id = (
        pending_change.session_row_id
    )

    original = (
        workspace.get_original_row(
            session_row_id
        )
    )

    current = (
        workspace.get_row(
            session_row_id
        )
    )

    row_id = _required_text(
        original.get(
            ROW_ID_COLUMN
        ),
        ROW_ID_COLUMN,
    )

    current_row_id = _required_text(
        current.get(
            ROW_ID_COLUMN
        ),
        ROW_ID_COLUMN,
    )

    if current_row_id != row_id:
        raise PersistenceBuildError(
            "row_id fue modificado dentro "
            "del Workspace."
        )

    expected_version = (
        _required_version(
            original.get(
                VERSION_COLUMN
            )
        )
    )

    current_version = (
        _required_version(
            current.get(
                VERSION_COLUMN
            )
        )
    )

    if (
        current_version
        != expected_version
    ):
        raise PersistenceBuildError(
            "version fue modificada dentro "
            "del Workspace."
        )

    persistent_changes = []

    editable_set = set(
        EDITABLE_COLUMNS
    )

    for change in (
        pending_change.changes
    ):
        column = change.column

        if column not in editable_set:
            raise PersistenceBuildError(
                "Se intento persistir una "
                "columna no editable: "
                f"{column}"
            )

        original_value = (
            original.get(column)
        )

        current_value = (
            current.get(column)
        )

        if (
            change.before
            != original_value
        ):
            raise PersistenceBuildError(
                "El valor anterior del cambio "
                "no coincide con la fila original "
                f"para {column}."
            )

        if (
            change.after
            != current_value
        ):
            raise PersistenceBuildError(
                "El valor final del cambio "
                "no coincide con el Workspace "
                f"para {column}."
            )

        persistent_changes.append(
            PersistenceFieldChange(
                column=column,
                before=deepcopy(
                    change.before
                ),
                after=deepcopy(
                    change.after
                ),
                value_type=(
                    EDITABLE_VALUE_TYPES[
                        column
                    ]
                ),
            )
        )

    if not persistent_changes:
        raise PersistenceBuildError(
            "La fila marcada como modificada "
            "no contiene cambios persistibles."
        )

    editable_values = []

    for column in EDITABLE_COLUMNS:
        if column not in current:
            raise PersistenceBuildError(
                "La fila no contiene la "
                "columna editable requerida: "
                f"{column}"
            )

        editable_values.append(
            (
                column,
                deepcopy(
                    current.get(column)
                ),
            )
        )

    return PersistenceRowChange(
        row_id=row_id,
        expected_version=(
            expected_version
        ),
        field_changes=tuple(
            persistent_changes
        ),
        editable_values=tuple(
            editable_values
        ),
    )


def build_persistence_batch(
    workspace,
    *,
    actor: str,
    app_version: str | None = None,
    timestamp: datetime | None = None,
    batch_id_factory=generate_batch_id,
) -> PersistenceBatch:
    actor_value = _required_text(
        actor,
        "actor",
    )

    pending_changes = (
        workspace.get_pending_changes()
    )

    if not pending_changes:
        raise PersistenceBuildError(
            "No existen cambios pendientes."
        )

    batch_id = _required_text(
        batch_id_factory(),
        "batch_id",
    )

    effective_timestamp = (
        timestamp
        if timestamp is not None
        else utc_now()
    )

    created_at = (
        _normalize_timestamp(
            effective_timestamp
        )
    )

    app_version_value = None

    if app_version is not None:
        normalized_version = str(
            app_version
        ).strip()

        if normalized_version:
            app_version_value = (
                normalized_version
            )

    rows = []

    seen_row_ids = set()

    for pending_change in (
        pending_changes
    ):
        row = _build_row_change(
            workspace,
            pending_change,
        )

        if row.row_id in seen_row_ids:
            raise PersistenceBuildError(
                "Existen row_id duplicados "
                "entre los cambios pendientes: "
                f"{row.row_id}"
            )

        seen_row_ids.add(
            row.row_id
        )

        rows.append(row)

    return PersistenceBatch(
        batch_id=batch_id,
        status=PENDING_STATUS,
        actor=actor_value,
        created_at=created_at,
        app_version=(
            app_version_value
        ),
        rows=tuple(rows),
    )
