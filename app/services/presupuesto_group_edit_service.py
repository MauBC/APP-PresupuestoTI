from copy import deepcopy
from dataclasses import dataclass
from decimal import (
    Decimal,
    ROUND_HALF_UP,
)
from typing import Any

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
)
from app.services.presupuesto_workspace import (
    SESSION_ROW_ID,
    PresupuestoWorkspace,
)
from app.services.proportional_allocation_service import (
    ProportionalAllocationError,
    ProportionalAllocationService,
)


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class PresupuestoGroupEditError(ValueError):
    pass


@dataclass(frozen=True)
class GroupEditPreview:
    group_columns: tuple[str, ...]
    group_values: tuple[Any, ...]
    column: str
    row_ids: tuple[int, ...]
    current_total: Decimal
    distribution_basis: Decimal
    target_total: Decimal
    difference: Decimal
    variation_percent: Decimal | None

    @property
    def row_count(self) -> int:
        return len(self.row_ids)


class PresupuestoGroupEditService:
    MAX_GROUP_COLUMNS = 3

    def __init__(
        self,
        workspace: PresupuestoWorkspace,
    ):
        self._workspace = workspace
        self._config = (
            workspace.module_config
        )

    def preview(
        self,
        *,
        group_columns,
        group_values,
        column: str,
        target_total,
    ) -> GroupEditPreview:
        columns = tuple(group_columns)
        values = tuple(group_values)

        self._validate_group(
            columns,
            values,
        )

        self._validate_usd_column(
            column
        )

        target = self._to_amount(
            target_total
        )

        rows = self._find_rows(
            columns,
            values,
        )

        if not rows:
            raise PresupuestoGroupEditError(
                "La agrupacion no contiene "
                "registros habilitados."
            )

        current_total = sum(
            (
                self._decimal(
                    row.get(column)
                )
                for row in rows
            ),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if (
            column
            == self._config.annual_column
        ):
            distribution_basis = sum(
                (
                    self._row_month_total(
                        row
                    )
                    for row in rows
                ),
                ZERO,
            )
        else:
            distribution_basis = (
                current_total
            )

        distribution_basis = (
            distribution_basis.quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )
        )

        if (
            target > ZERO
            and
            distribution_basis == ZERO
        ):
            raise PresupuestoGroupEditError(
                "El grupo no tiene una "
                "distribucion previa distinta de "
                "cero. Se debe elegir primero "
                "una estrategia de distribucion."
            )

        difference = (
            target - current_total
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if current_total == ZERO:
            variation_percent = None
        else:
            variation_percent = (
                difference
                / current_total
                * Decimal("100")
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

        return GroupEditPreview(
            group_columns=columns,
            group_values=values,
            column=column,
            row_ids=tuple(
                row[SESSION_ROW_ID]
                for row in rows
            ),
            current_total=current_total,
            distribution_basis=(
                distribution_basis
            ),
            target_total=target,
            difference=difference,
            variation_percent=(
                variation_percent
            ),
        )

    def apply(
        self,
        *,
        group_columns,
        group_values,
        column: str,
        target_total,
    ) -> GroupEditPreview:
        preview = self.preview(
            group_columns=group_columns,
            group_values=group_values,
            column=column,
            target_total=target_total,
        )

        if (
            preview.target_total
            == preview.current_total
        ):
            return preview

        if (
            column
            == self._config.annual_column
        ):
            replacements = (
                self._build_annual_replacements(
                    preview.row_ids,
                    preview.target_total,
                )
            )
        else:
            replacements = (
                self._build_month_replacements(
                    preview.row_ids,
                    column,
                    preview.target_total,
                )
            )

        description = (
            "Editar agrupacion "
            + " / ".join(
                f"{column_name}={value}"
                for column_name, value
                in zip(
                    preview.group_columns,
                    preview.group_values,
                )
            )
            + f" | {column}: "
            + f"{preview.current_total} -> "
            + f"{preview.target_total}"
        )

        self._workspace.apply_batch(
            description=description,
            replacements=replacements,
        )

        return preview

    def get_group_row_ids(
        self,
        *,
        group_columns,
        group_values,
        enabled=None,
    ) -> tuple[int, ...]:
        columns = tuple(
            group_columns
        )

        values = tuple(
            group_values
        )

        self._validate_group(
            columns,
            values,
        )

        if (
            enabled is not None
            and
            not isinstance(
                enabled,
                bool,
            )
        ):
            raise PresupuestoGroupEditError(
                "enabled debe ser bool o None."
            )

        result = []

        for row in (
            self._workspace.iter_rows()
        ):
            matches = all(
                row.get(column) == value
                for column, value
                in zip(
                    columns,
                    values,
                )
            )

            if not matches:
                continue

            row_enabled = bool(
                row.get(
                    HABILITADO_COLUMN,
                    True,
                )
            )

            if (
                enabled is not None
                and
                row_enabled != enabled
            ):
                continue

            result.append(
                row[
                    SESSION_ROW_ID
                ]
            )

        return tuple(
            result
        )

    def set_group_enabled(
        self,
        *,
        group_columns,
        group_values,
        enabled: bool,
    ) -> int:
        if not isinstance(
            enabled,
            bool,
        ):
            raise PresupuestoGroupEditError(
                "enabled debe ser bool."
            )

        columns = tuple(
            group_columns
        )

        values = tuple(
            group_values
        )

        row_ids = (
            self.get_group_row_ids(
                group_columns=columns,
                group_values=values,
                enabled=not enabled,
            )
        )

        if not row_ids:
            return 0

        replacements = {}

        for row_id in row_ids:
            updated = deepcopy(
                self._workspace.get_row(
                    row_id
                )
            )

            updated[
                HABILITADO_COLUMN
            ] = enabled

            replacements[
                row_id
            ] = updated

        action = (
            "Reactivar agrupacion"
            if enabled
            else "Deshabilitar agrupacion"
        )

        description = (
            action
            + " | "
            + " / ".join(
                f"{column}={value}"
                for column, value
                in zip(
                    columns,
                    values,
                )
            )
        )

        changed = (
            self._workspace.apply_batch(
                description=description,
                replacements=replacements,
            )
        )

        if not changed:
            return 0

        return len(
            row_ids
        )

    def _find_rows(
        self,
        columns,
        values,
    ):
        rows = []

        for row in self._workspace.iter_rows():
            if not bool(
                row.get(
                    HABILITADO_COLUMN,
                    True,
                )
            ):
                continue

            matches = all(
                row.get(column) == value
                for column, value
                in zip(
                    columns,
                    values,
                )
            )

            if matches:
                rows.append(
                    dict(row)
                )

        return rows

    def _build_month_replacements(
        self,
        row_ids,
        column,
        target,
    ):
        rows = {
            row_id: self._workspace.get_row(
                row_id
            )
            for row_id in row_ids
        }

        values = []

        for row_id, row in rows.items():
            value = row.get(column)

            if value is None:
                continue

            amount = self._decimal(
                value
            )

            self._validate_existing_amount(
                amount
            )

            values.append(
                (
                    row_id,
                    amount,
                )
            )

        allocated = self._allocate(
            values,
            target,
        )

        replacements = {}

        for row_id, row in rows.items():
            updated = deepcopy(
                row
            )

            if row_id in allocated:
                updated[column] = (
                    allocated[row_id]
                )

            updated[
                self._config.annual_column
            ] = self._row_month_total(
                updated
            )

            replacements[row_id] = (
                updated
            )

        return replacements

    def _build_annual_replacements(
        self,
        row_ids,
        target,
    ):
        rows = {
            row_id: self._workspace.get_row(
                row_id
            )
            for row_id in row_ids
        }

        cells = []

        for row_id, row in rows.items():
            for month in (
                self._config.month_columns
            ):
                value = row.get(
                    month
                )

                if value is None:
                    continue

                amount = self._decimal(
                    value
                )

                self._validate_existing_amount(
                    amount
                )

                cells.append(
                    (
                        (
                            row_id,
                            month,
                        ),
                        amount,
                    )
                )

        allocated = self._allocate(
            cells,
            target,
        )

        replacements = {}

        for row_id, row in rows.items():
            updated = deepcopy(
                row
            )

            for month in (
                self._config.month_columns
            ):
                key = (
                    row_id,
                    month,
                )

                if key in allocated:
                    updated[month] = (
                        allocated[key]
                    )

            updated[
                self._config.annual_column
            ] = self._row_month_total(
                updated
            )

            replacements[row_id] = (
                updated
            )

        return replacements

    def _allocate(
        self,
        values,
        target,
    ):
        try:
            return (
                ProportionalAllocationService
                .allocate(
                    values,
                    target,
                )
            )

        except ProportionalAllocationError as exc:
            raise PresupuestoGroupEditError(
                str(exc)
            ) from exc

    def _validate_group(
        self,
        columns,
        values,
    ):
        if not columns:
            raise PresupuestoGroupEditError(
                "Debe existir al menos una "
                "dimension de agrupacion."
            )

        if (
            len(columns)
            > self.MAX_GROUP_COLUMNS
        ):
            raise PresupuestoGroupEditError(
                "Solo se permiten hasta "
                f"{self.MAX_GROUP_COLUMNS} "
                "dimensiones."
            )

        if len(columns) != len(set(columns)):
            raise PresupuestoGroupEditError(
                "No se puede repetir una "
                "dimension."
            )

        if len(columns) != len(values):
            raise PresupuestoGroupEditError(
                "Las dimensiones y sus valores "
                "no coinciden."
            )

        invalid = [
            column
            for column in columns
            if (
                column
                not in
                self._config.groupable_columns
            )
        ]

        if invalid:
            raise PresupuestoGroupEditError(
                "Dimensiones no validas: "
                + ", ".join(invalid)
            )

    def _validate_usd_column(
        self,
        column,
    ):
        if (
            column
            not in
            self._config.amount_columns
        ):
            raise PresupuestoGroupEditError(
                f"La columna {column} "
                "no es editable como importe."
            )

    @staticmethod
    def _validate_existing_amount(
        amount,
    ):
        if amount < ZERO:
            raise PresupuestoGroupEditError(
                "No se puede redistribuir un "
                "grupo que contiene importes "
                "negativos."
            )

    @staticmethod
    def _decimal(
        value,
    ) -> Decimal:
        if value is None:
            return ZERO

        if isinstance(
            value,
            Decimal,
        ):
            return value

        return Decimal(
            str(value)
        )

    @classmethod
    def _to_amount(
        cls,
        value,
    ) -> Decimal:
        amount = cls._decimal(
            value
        )

        if amount < ZERO:
            raise PresupuestoGroupEditError(
                "El presupuesto no puede "
                "ser negativo."
            )

        return amount.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    def _row_month_total(
        self,
        row,
    ) -> Decimal:
        return sum(
            (
                self._decimal(
                    row.get(month)
                )
                for month
                in self._config.month_columns
            ),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )
