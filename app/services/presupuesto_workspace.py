from copy import deepcopy
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from app.config.budget_module_config import (
    BudgetModuleConfig,
)
from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
    ROW_ID_COLUMN,
    USD_COLUMNS,
    VERSION_COLUMN,
)
from app.models.workspace_change import (
    ChangeBatch,
    FieldChange,
    PendingRowChange,
    RowStateChange,
)
from app.services.usd_allocation_service import (
    UsdAllocationService,
)


SESSION_ROW_ID = "_session_row_id"


class PresupuestoWorkspaceError(ValueError):
    pass


class PresupuestoWorkspace:
    def __init__(
        self,
        module_config:
            BudgetModuleConfig | None = None,
    ):
        self._module_config = (
            module_config
            if module_config is not None
            else OPEX_MODULE_CONFIG
        )

        self._original_rows: dict[
            int,
            dict[str, Any],
        ] = {}

        self._working_rows: dict[
            int,
            dict[str, Any],
        ] = {}

        self._history: list[
            ChangeBatch
        ] = []

        self._dirty_row_ids: set[int] = set()

        self._loaded = False

    @property
    def module_config(
        self,
    ) -> BudgetModuleConfig:
        return self._module_config

    @property
    def amount_columns(
        self,
    ) -> tuple[str, ...]:
        return (
            self._module_config
            .amount_columns
        )

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def row_count(self) -> int:
        return len(self._working_rows)

    @property
    def history_count(self) -> int:
        return len(self._history)

    @property
    def pending_row_count(self) -> int:
        return len(self._dirty_row_ids)

    @property
    def has_changes(self) -> bool:
        return bool(self._dirty_row_ids)

    @property
    def pending_change_count(self) -> int:
        return sum(
            len(change.changes)
            for change in self.get_pending_changes()
        )

    @staticmethod
    def _normalize_enabled(
        value,
    ) -> bool:
        if value is None:
            return True

        if isinstance(value, bool):
            return value

        if isinstance(value, int):
            if value == 1:
                return True

            if value == 0:
                return False

        text = str(value).strip().lower()

        if text in {
            "true",
            "1",
            "si",
            "sí",
            "yes",
        }:
            return True

        if text in {
            "false",
            "0",
            "no",
        }:
            return False

        raise PresupuestoWorkspaceError(
            "Valor no valido para habilitado: "
            f"{value!r}"
        )

    def load(
        self,
        rows: Iterable[
            Mapping[str, Any]
        ],
    ) -> None:
        original_rows = {}

        required_columns = set(
            self._module_config
            .amount_columns
        )

        for index, source_row in enumerate(rows):
            row = deepcopy(
                dict(source_row)
            )

            missing_columns = (
                required_columns
                - set(row)
            )

            if missing_columns:
                raise PresupuestoWorkspaceError(
                    "La fila "
                    f"{index} no contiene todas "
                    "las columnas USD requeridas: "
                    + ", ".join(
                        sorted(missing_columns)
                    )
                )

            row[HABILITADO_COLUMN] = (
                self._normalize_enabled(
                    row.get(
                        HABILITADO_COLUMN,
                        True,
                    )
                )
            )

            row[SESSION_ROW_ID] = index

            original_rows[index] = row

        self._original_rows = original_rows

        self._working_rows = deepcopy(
            original_rows
        )

        self._history.clear()
        self._dirty_row_ids.clear()

        self._loaded = True

    def iter_rows(
        self,
    ):
        self._require_loaded()

        for row_id in sorted(
            self._working_rows
        ):
            yield MappingProxyType(
                self._working_rows[row_id]
            )

    def get_rows(
        self,
    ) -> tuple[dict[str, Any], ...]:
        self._require_loaded()

        return tuple(
            deepcopy(
                self._working_rows[row_id]
            )
            for row_id in sorted(
                self._working_rows
            )
        )

    def get_row(
        self,
        session_row_id: int,
    ) -> dict[str, Any]:
        row = self._require_row(
            session_row_id
        )

        return deepcopy(row)

    def get_original_row(
        self,
        session_row_id: int,
    ) -> dict[str, Any]:
        self._require_loaded()

        if (
            session_row_id
            not in self._original_rows
        ):
            raise PresupuestoWorkspaceError(
                "No existe la fila "
                f"{session_row_id}."
            )

        return deepcopy(
            self._original_rows[
                session_row_id
            ]
        )

    def reconcile_persisted_rows(
        self,
        rows: Iterable[
            Mapping[str, Any]
        ],
    ) -> int:
        self._require_loaded()

        if not self._dirty_row_ids:
            return 0

        session_by_row_id = {}

        for session_row_id, row in (
            self._original_rows.items()
        ):
            persistent_row_id = str(
                row.get(
                    ROW_ID_COLUMN,
                    ""
                )
                or ""
            ).strip()

            if not persistent_row_id:
                raise PresupuestoWorkspaceError(
                    "Una fila del Workspace "
                    "no contiene row_id."
                )

            if (
                persistent_row_id
                in session_by_row_id
            ):
                raise PresupuestoWorkspaceError(
                    "El Workspace contiene "
                    "row_id duplicados."
                )

            session_by_row_id[
                persistent_row_id
            ] = session_row_id

        expected_row_ids = set()

        for session_row_id in (
            self._dirty_row_ids
        ):
            row_id = str(
                self._original_rows[
                    session_row_id
                ].get(
                    ROW_ID_COLUMN,
                    ""
                )
                or ""
            ).strip()

            if not row_id:
                raise PresupuestoWorkspaceError(
                    "Una fila modificada "
                    "no contiene row_id."
                )

            expected_row_ids.add(
                row_id
            )

        required_columns = {
            ROW_ID_COLUMN,
            VERSION_COLUMN,
            *self._module_config.amount_columns,
        }

        replacements = {}
        received_row_ids = set()

        for index, source_row in enumerate(
            rows
        ):
            row = deepcopy(
                dict(source_row)
            )

            missing_columns = (
                required_columns
                - set(row)
            )

            if missing_columns:
                raise PresupuestoWorkspaceError(
                    "La fila persistida "
                    f"{index} no contiene: "
                    + ", ".join(
                        sorted(
                            missing_columns
                        )
                    )
                )

            persistent_row_id = str(
                row.get(
                    ROW_ID_COLUMN,
                    ""
                )
                or ""
            ).strip()

            if not persistent_row_id:
                raise PresupuestoWorkspaceError(
                    "BigQuery devolvio una "
                    "fila sin row_id."
                )

            if (
                persistent_row_id
                in received_row_ids
            ):
                raise PresupuestoWorkspaceError(
                    "BigQuery devolvio "
                    "row_id duplicados."
                )

            if (
                persistent_row_id
                not in expected_row_ids
            ):
                raise PresupuestoWorkspaceError(
                    "BigQuery devolvio una "
                    "fila que no pertenecia "
                    "al guardado."
                )

            session_row_id = (
                session_by_row_id.get(
                    persistent_row_id
                )
            )

            if session_row_id is None:
                raise PresupuestoWorkspaceError(
                    "No se encontro row_id "
                    "persistido en el Workspace."
                )

            row[
                HABILITADO_COLUMN
            ] = self._normalize_enabled(
                row.get(
                    HABILITADO_COLUMN,
                    True,
                )
            )

            row[
                SESSION_ROW_ID
            ] = session_row_id

            replacements[
                session_row_id
            ] = row

            received_row_ids.add(
                persistent_row_id
            )

        missing_rows = (
            expected_row_ids
            - received_row_ids
        )

        if missing_rows:
            raise PresupuestoWorkspaceError(
                "No se pudieron recargar "
                "todas las filas aplicadas."
            )

        for session_row_id, row in (
            replacements.items()
        ):
            self._original_rows[
                session_row_id
            ] = deepcopy(
                row
            )

            self._working_rows[
                session_row_id
            ] = deepcopy(
                row
            )

        self._history.clear()
        self._dirty_row_ids.clear()

        return len(
            replacements
        )

    def edit_month(
        self,
        session_row_id: int,
        column: str,
        value,
    ) -> bool:
        current = self._require_row(
            session_row_id
        )

        updated = (
            UsdAllocationService.set_month(
                current,
                column,
                value,
                month_columns=(
                    self._module_config
                    .month_columns
                ),
                annual_column=(
                    self._module_config
                    .annual_column
                ),
            )
        )

        return self._apply_batch(
            description=(
                f"Editar {column} "
                f"en fila {session_row_id}"
            ),
            replacements={
                session_row_id: updated,
            },
        )

    def edit_annual(
        self,
        session_row_id: int,
        value,
    ) -> bool:
        current = self._require_row(
            session_row_id
        )

        updated = (
            UsdAllocationService
            .set_annual_total(
                current,
                value,
                month_columns=(
                    self._module_config
                    .month_columns
                ),
                annual_column=(
                    self._module_config
                    .annual_column
                ),
            )
        )

        return self._apply_batch(
            description=(
                "Editar anio_usd "
                f"en fila {session_row_id}"
            ),
            replacements={
                session_row_id: updated,
            },
        )

    def edit_monthly_distribution(
        self,
        session_row_id: int,
        percentages,
        *,
        annual_total=None,
    ) -> bool:
        if not (
            self._module_config
            .capabilities
            .monthly_distribution
        ):
            raise PresupuestoWorkspaceError(
                "El modulo activo no permite "
                "distribucion mensual."
            )

        current = self._require_row(
            session_row_id
        )

        updated = (
            UsdAllocationService
            .set_percentage_distribution(
                current,
                percentages,
                total=annual_total,
                month_columns=(
                    self._module_config
                    .month_columns
                ),
                annual_column=(
                    self._module_config
                    .annual_column
                ),
            )
        )

        return self._apply_batch(
            description=(
                "Distribuir presupuesto mensual "
                f"en fila {session_row_id}"
            ),
            replacements={
                session_row_id: updated,
            },
        )

    def set_enabled(
        self,
        session_row_id: int,
        enabled: bool,
    ) -> bool:
        current = self._require_row(
            session_row_id
        )

        updated = deepcopy(current)

        updated[HABILITADO_COLUMN] = bool(
            enabled
        )

        action = (
            "Habilitar"
            if enabled
            else "Deshabilitar"
        )

        return self._apply_batch(
            description=(
                f"{action} fila "
                f"{session_row_id}"
            ),
            replacements={
                session_row_id: updated,
            },
        )

    def apply_batch(
        self,
        *,
        description: str,
        replacements: Mapping[
            int,
            Mapping[str, Any],
        ],
    ) -> bool:
        return self._apply_batch(
            description=description,
            replacements=replacements,
        )

    def undo_last(
        self,
    ) -> bool:
        self._require_loaded()

        if not self._history:
            return False

        batch = self._history.pop()

        for change in batch.rows:
            self._working_rows[
                change.session_row_id
            ] = deepcopy(
                change.before
            )

            self._refresh_dirty_state(
                change.session_row_id
            )

        return True

    def discard_all(
        self,
    ) -> None:
        self._require_loaded()

        self._working_rows = deepcopy(
            self._original_rows
        )

        self._history.clear()
        self._dirty_row_ids.clear()

    def get_pending_changes(
        self,
    ) -> tuple[
        PendingRowChange,
        ...
    ]:
        self._require_loaded()

        pending = []

        for row_id in sorted(
            self._dirty_row_ids
        ):
            original = (
                self._original_rows[row_id]
            )

            working = (
                self._working_rows[row_id]
            )

            columns = (
                set(original)
                | set(working)
            )

            columns.discard(
                SESSION_ROW_ID
            )

            changes = []

            for column in sorted(columns):
                before = original.get(
                    column
                )

                after = working.get(
                    column
                )

                if before == after:
                    continue

                changes.append(
                    FieldChange(
                        column=column,
                        before=deepcopy(
                            before
                        ),
                        after=deepcopy(
                            after
                        ),
                    )
                )

            if changes:
                pending.append(
                    PendingRowChange(
                        session_row_id=row_id,
                        changes=tuple(changes),
                    )
                )

        return tuple(pending)

    def _apply_batch(
        self,
        *,
        description: str,
        replacements: Mapping[
            int,
            Mapping[str, Any],
        ],
    ) -> bool:
        self._require_loaded()

        changes = []

        for row_id, new_row in (
            replacements.items()
        ):
            current = self._require_row(
                row_id
            )

            updated = deepcopy(
                dict(new_row)
            )

            updated[
                SESSION_ROW_ID
            ] = row_id

            if current == updated:
                continue

            changes.append(
                RowStateChange(
                    session_row_id=row_id,
                    before=deepcopy(
                        current
                    ),
                    after=deepcopy(
                        updated
                    ),
                )
            )

        if not changes:
            return False

        for change in changes:
            self._working_rows[
                change.session_row_id
            ] = deepcopy(
                change.after
            )

            self._refresh_dirty_state(
                change.session_row_id
            )

        self._history.append(
            ChangeBatch(
                description=description,
                rows=tuple(changes),
            )
        )

        return True

    def _refresh_dirty_state(
        self,
        session_row_id: int,
    ) -> None:
        original = (
            self._original_rows[
                session_row_id
            ]
        )

        working = (
            self._working_rows[
                session_row_id
            ]
        )

        if working == original:
            self._dirty_row_ids.discard(
                session_row_id
            )
        else:
            self._dirty_row_ids.add(
                session_row_id
            )

    def _require_loaded(
        self,
    ) -> None:
        if not self._loaded:
            raise PresupuestoWorkspaceError(
                "El workspace no contiene "
                "un presupuesto cargado."
            )

    def _require_row(
        self,
        session_row_id: int,
    ) -> dict[str, Any]:
        self._require_loaded()

        if (
            session_row_id
            not in self._working_rows
        ):
            raise PresupuestoWorkspaceError(
                "No existe la fila "
                f"{session_row_id}."
            )

        return self._working_rows[
            session_row_id
        ]