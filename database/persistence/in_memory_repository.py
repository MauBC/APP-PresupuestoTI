from copy import deepcopy
from dataclasses import replace
from typing import (
    Any,
    Iterable,
    Mapping,
)

from app.config.presupuesto_app_config import (
    CREATED_AT_COLUMN,
    CREATED_BY_COLUMN,
    ROW_ID_COLUMN,
    UPDATED_AT_COLUMN,
    UPDATED_BY_COLUMN,
    VERSION_COLUMN,
)
from database.persistence.contract import (
    APPLIED_STATUS,
    CONFLICT_STATUS,
    EDITABLE_COLUMNS,
    PENDING_STATUS,
)
from database.persistence.models import (
    AuditChange,
    ConflictDetail,
    PersistenceBatch,
    PersistenceResult,
    StagingRow,
)


class InMemoryPersistenceError(
    ValueError
):
    pass


class InMemoryPersistenceRepository:
    def __init__(
        self,
        rows: Iterable[
            Mapping[str, Any]
        ] = (),
    ):
        self._rows = {}
        self._batches = {}
        self._staging = {}
        self._audit = []

        for source_row in rows:
            row = deepcopy(
                dict(source_row)
            )

            row_id = self._required_row_id(
                row.get(
                    ROW_ID_COLUMN
                )
            )

            version = self._required_version(
                row.get(
                    VERSION_COLUMN
                )
            )

            if row_id in self._rows:
                raise (
                    InMemoryPersistenceError(
                        "row_id duplicado "
                        "en repositorio: "
                        f"{row_id}"
                    )
                )

            row[
                ROW_ID_COLUMN
            ] = row_id

            row[
                VERSION_COLUMN
            ] = version

            self._rows[
                row_id
            ] = row

    def create_batch(
        self,
        batch: PersistenceBatch,
    ) -> None:
        if (
            batch.status
            != PENDING_STATUS
        ):
            raise (
                InMemoryPersistenceError(
                    "Solo se puede registrar "
                    "un batch PENDING."
                )
            )

        if (
            batch.batch_id
            in self._batches
        ):
            raise (
                InMemoryPersistenceError(
                    "El batch_id ya existe: "
                    f"{batch.batch_id}"
                )
            )

        self._batches[
            batch.batch_id
        ] = batch

    def stage_rows(
        self,
        rows: Iterable[
            StagingRow
        ],
    ) -> None:
        staging_rows = tuple(
            rows
        )

        if not staging_rows:
            raise (
                InMemoryPersistenceError(
                    "No existen filas "
                    "para staging."
                )
            )

        batch_ids = {
            row.batch_id
            for row in staging_rows
        }

        if len(batch_ids) != 1:
            raise (
                InMemoryPersistenceError(
                    "Todas las filas staging "
                    "deben pertenecer al "
                    "mismo batch."
                )
            )

        batch_id = next(
            iter(batch_ids)
        )

        batch = self._require_batch(
            batch_id
        )

        if (
            batch.status
            != PENDING_STATUS
        ):
            raise (
                InMemoryPersistenceError(
                    "El batch no se encuentra "
                    "PENDING."
                )
            )

        seen = set()

        for row in staging_rows:
            if row.row_id in seen:
                raise (
                    InMemoryPersistenceError(
                        "row_id duplicado "
                        "en staging: "
                        f"{row.row_id}"
                    )
                )

            seen.add(
                row.row_id
            )

        if (
            len(staging_rows)
            != batch.row_count
        ):
            raise (
                InMemoryPersistenceError(
                    "La cantidad de filas "
                    "staging no coincide con "
                    "el batch."
                )
            )

        self._staging[
            batch_id
        ] = staging_rows

    def find_conflicts(
        self,
        batch_id: str,
    ) -> tuple[
        ConflictDetail,
        ...
    ]:
        staging = self._require_staging(
            batch_id
        )

        conflicts = []

        for staged_row in staging:
            current = self._rows.get(
                staged_row.row_id
            )

            if staged_row.is_insert:
                if current is not None:
                    current_version = (
                        self._required_version(
                            current.get(
                                VERSION_COLUMN
                            )
                        )
                    )

                    conflicts.append(
                        ConflictDetail(
                            row_id=(
                                staged_row.row_id
                            ),
                            expected_version=0,
                            current_version=(
                                current_version
                            ),
                        )
                    )

                continue

            if current is None:
                conflicts.append(
                    ConflictDetail(
                        row_id=(
                            staged_row.row_id
                        ),
                        expected_version=(
                            staged_row
                            .expected_version
                        ),
                        current_version=None,
                    )
                )

                continue

            current_version = (
                self._required_version(
                    current.get(
                        VERSION_COLUMN
                    )
                )
            )

            if (
                current_version
                != staged_row
                .expected_version
            ):
                conflicts.append(
                    ConflictDetail(
                        row_id=(
                            staged_row.row_id
                        ),
                        expected_version=(
                            staged_row
                            .expected_version
                        ),
                        current_version=(
                            current_version
                        ),
                    )
                )

        return tuple(
            conflicts
        )

    def apply_staged_batch(
        self,
        batch_id: str,
        audit_changes: Iterable[
            AuditChange
        ],
    ) -> PersistenceResult:
        batch = self._require_batch(
            batch_id
        )

        staging = self._require_staging(
            batch_id
        )

        if (
            batch.status
            != PENDING_STATUS
        ):
            raise (
                InMemoryPersistenceError(
                    "Solo se puede aplicar "
                    "un batch PENDING."
                )
            )

        conflicts = (
            self.find_conflicts(
                batch_id
            )
        )

        if conflicts:
            self._batches[
                batch_id
            ] = replace(
                batch,
                status=(
                    CONFLICT_STATUS
                ),
            )

            self._staging.pop(
                batch_id,
                None,
            )

            return PersistenceResult(
                batch_id=batch_id,
                status=CONFLICT_STATUS,
                row_count=(
                    batch.row_count
                ),
                field_count=(
                    batch.field_count
                ),
                conflicts=conflicts,
            )

        audit = tuple(
            audit_changes
        )

        self._validate_audit(
            batch,
            audit,
        )

        updated_rows = deepcopy(
            self._rows
        )

        for staged_row in staging:
            editable = dict(
                staged_row.editable_values
            )

            if (
                tuple(editable)
                != EDITABLE_COLUMNS
            ):
                raise (
                    InMemoryPersistenceError(
                        "Staging no coincide "
                        "con el contrato editable."
                    )
                )

            if staged_row.is_insert:
                current = deepcopy(
                    dict(
                        staged_row
                        .insert_values
                    )
                )

                for (
                    column,
                    value,
                ) in editable.items():
                    current[
                        column
                    ] = deepcopy(
                        value
                    )

                current[
                    ROW_ID_COLUMN
                ] = staged_row.row_id

                current[
                    VERSION_COLUMN
                ] = 1

                current[
                    CREATED_AT_COLUMN
                ] = batch.created_at

                current[
                    CREATED_BY_COLUMN
                ] = batch.actor

                current[
                    UPDATED_AT_COLUMN
                ] = batch.created_at

                current[
                    UPDATED_BY_COLUMN
                ] = batch.actor

                updated_rows[
                    staged_row.row_id
                ] = current

                continue

            current = deepcopy(
                updated_rows[
                    staged_row.row_id
                ]
            )

            for (
                column,
                value,
            ) in staged_row.insert_values:
                current[column] = deepcopy(value)

            for (
                column,
                value,
            ) in editable.items():
                current[
                    column
                ] = deepcopy(
                    value
                )

            current[
                VERSION_COLUMN
            ] = (
                staged_row
                .expected_version
                + 1
            )

            updated_rows[
                staged_row.row_id
            ] = current

        self._rows = updated_rows

        self._audit.extend(
            audit
        )

        self._batches[
            batch_id
        ] = replace(
            batch,
            status=APPLIED_STATUS,
        )

        self._staging.pop(
            batch_id,
            None,
        )

        return PersistenceResult(
            batch_id=batch_id,
            status=APPLIED_STATUS,
            row_count=(
                batch.row_count
            ),
            field_count=(
                batch.field_count
            ),
        )

    def get_row(
        self,
        row_id: str,
    ) -> dict[str, Any]:
        row = self._rows.get(
            row_id
        )

        if row is None:
            raise KeyError(
                row_id
            )

        return deepcopy(
            row
        )

    def get_batch(
        self,
        batch_id: str,
    ) -> PersistenceBatch:
        return self._require_batch(
            batch_id
        )

    def get_audit(
        self,
    ) -> tuple[
        AuditChange,
        ...
    ]:
        return tuple(
            self._audit
        )

    def has_staging(
        self,
        batch_id: str,
    ) -> bool:
        return (
            batch_id
            in self._staging
        )

    def _validate_audit(
        self,
        batch,
        audit,
    ):
        if (
            len(audit)
            != batch.field_count
        ):
            raise (
                InMemoryPersistenceError(
                    "La cantidad de auditorias "
                    "no coincide con field_count."
                )
            )

        audit_ids = set()

        for change in audit:
            if (
                change.batch_id
                != batch.batch_id
            ):
                raise (
                    InMemoryPersistenceError(
                        "La auditoria pertenece "
                        "a otro batch."
                    )
                )

            if (
                change.audit_id
                in audit_ids
            ):
                raise (
                    InMemoryPersistenceError(
                        "audit_id duplicado."
                    )
                )

            audit_ids.add(
                change.audit_id
            )

    def _require_batch(
        self,
        batch_id,
    ) -> PersistenceBatch:
        batch = self._batches.get(
            batch_id
        )

        if batch is None:
            raise (
                InMemoryPersistenceError(
                    "No existe el batch: "
                    f"{batch_id}"
                )
            )

        return batch

    def _require_staging(
        self,
        batch_id,
    ) -> tuple[
        StagingRow,
        ...
    ]:
        staging = (
            self._staging.get(
                batch_id
            )
        )

        if staging is None:
            raise (
                InMemoryPersistenceError(
                    "No existe staging "
                    "para el batch: "
                    f"{batch_id}"
                )
            )

        return staging

    @staticmethod
    def _required_row_id(
        value,
    ) -> str:
        text = str(
            value
            if value is not None
            else ""
        ).strip()

        if not text:
            raise (
                InMemoryPersistenceError(
                    "row_id no puede "
                    "estar vacio."
                )
            )

        return text

    @staticmethod
    def _required_version(
        value,
    ) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                int,
            )
            or value < 1
        ):
            raise (
                InMemoryPersistenceError(
                    "version debe ser "
                    "un entero >= 1."
                )
            )

        return value
