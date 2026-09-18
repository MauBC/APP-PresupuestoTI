from copy import deepcopy
from dataclasses import dataclass
from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)
from typing import Any

from app.config.grouping_config import (
    MAX_GROUPING_LEVELS,
)
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
HUNDRED = Decimal("100")


class DimensionAllocationError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
)
class DimensionAllocationItem:
    value: Any
    row_ids: tuple[int, ...]
    current_total: Decimal
    percentage: Decimal
    target_total: Decimal
    difference: Decimal
    variation_percent: Decimal | None

    @property
    def row_count(
        self,
    ) -> int:
        return len(
            self.row_ids
        )


@dataclass(
    frozen=True,
)
class DimensionAllocationPreview:
    dimension: str
    scope_columns: tuple[str, ...]
    scope_values: tuple[Any, ...]
    row_ids: tuple[int, ...]
    current_total: Decimal
    percentage_total: Decimal
    items: tuple[
        DimensionAllocationItem,
        ...
    ]

    @property
    def row_count(
        self,
    ) -> int:
        return len(
            self.row_ids
        )

    @property
    def dimension_count(
        self,
    ) -> int:
        return len(
            self.items
        )


class DimensionAllocationService:
    MAX_SCOPE_COLUMNS = MAX_GROUPING_LEVELS

    def __init__(
        self,
        workspace:
            PresupuestoWorkspace,
    ):
        self._workspace = workspace
        self._config = (
            workspace.module_config
        )

    def current_preview(
        self,
        *,
        dimension: str,
        scope_columns=(),
        scope_values=(),
    ) -> DimensionAllocationPreview:
        self._validate_dimension(
            dimension
        )

        columns = tuple(
            scope_columns
        )

        values = tuple(
            scope_values
        )

        self._validate_scope(
            dimension,
            columns,
            values,
        )

        rows = self._find_rows(
            columns,
            values,
        )

        if not rows:
            raise DimensionAllocationError(
                "El alcance seleccionado no "
                "contiene registros habilitados."
            )

        groups = self._group_rows(
            rows,
            dimension,
        )

        percentages = (
            self._current_percentages(
                groups
            )
        )

        current_total = sum(
            (
                self._annual_amount(
                    row
                )
                for row in rows
            ),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        items = []

        for value, group_rows in (
            groups.items()
        ):
            current = sum(
                (
                    self._annual_amount(
                        row
                    )
                    for row
                    in group_rows
                ),
                ZERO,
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

            items.append(
                DimensionAllocationItem(
                    value=value,
                    row_ids=tuple(
                        row[
                            SESSION_ROW_ID
                        ]
                        for row
                        in group_rows
                    ),
                    current_total=current,
                    percentage=(
                        percentages[value]
                    ),
                    target_total=current,
                    difference=ZERO,
                    variation_percent=(
                        None
                        if current == ZERO
                        else ZERO
                    ),
                )
            )

        return DimensionAllocationPreview(
            dimension=dimension,
            scope_columns=columns,
            scope_values=values,
            row_ids=tuple(
                row[
                    SESSION_ROW_ID
                ]
                for row in rows
            ),
            current_total=current_total,
            percentage_total=sum(
                percentages.values(),
                ZERO,
            ),
            items=tuple(
                items
            ),
        )

    def current_percentages(
        self,
        *,
        dimension: str,
        scope_columns=(),
        scope_values=(),
    ):
        preview = self.current_preview(
            dimension=dimension,
            scope_columns=scope_columns,
            scope_values=scope_values,
        )

        return {
            item.value:
                item.percentage
            for item in preview.items
        }

    def preview(
        self,
        *,
        dimension: str,
        percentages,
        scope_columns=(),
        scope_values=(),
    ) -> DimensionAllocationPreview:
        self._validate_dimension(
            dimension
        )

        columns = tuple(
            scope_columns
        )

        values = tuple(
            scope_values
        )

        self._validate_scope(
            dimension,
            columns,
            values,
        )

        rows = self._find_rows(
            columns,
            values,
        )

        if not rows:
            raise DimensionAllocationError(
                "El alcance seleccionado no "
                "contiene registros habilitados."
            )

        groups = self._group_rows(
            rows,
            dimension,
        )

        normalized = (
            self._validate_percentages(
                groups,
                percentages,
            )
        )

        current_total = sum(
            (
                self._annual_amount(
                    row
                )
                for row in rows
            ),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        try:
            targets = (
                ProportionalAllocationService
                .allocate(
                    (
                        (
                            value,
                            normalized[value],
                        )
                        for value in groups
                    ),
                    current_total,
                )
            )

        except ProportionalAllocationError as exc:
            raise DimensionAllocationError(
                str(exc)
            ) from exc

        items = []

        for value, group_rows in (
            groups.items()
        ):
            current = sum(
                (
                    self._annual_amount(
                        row
                    )
                    for row
                    in group_rows
                ),
                ZERO,
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

            target = targets[
                value
            ]

            self._validate_group_basis(
                group_rows,
                target,
            )

            difference = (
                target
                - current
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

            if current == ZERO:
                variation = None
            else:
                variation = (
                    difference
                    / current
                    * HUNDRED
                ).quantize(
                    CENT,
                    rounding=ROUND_HALF_UP,
                )

            items.append(
                DimensionAllocationItem(
                    value=value,
                    row_ids=tuple(
                        row[
                            SESSION_ROW_ID
                        ]
                        for row
                        in group_rows
                    ),
                    current_total=current,
                    percentage=(
                        normalized[value]
                    ),
                    target_total=target,
                    difference=difference,
                    variation_percent=(
                        variation
                    ),
                )
            )

        return DimensionAllocationPreview(
            dimension=dimension,
            scope_columns=columns,
            scope_values=values,
            row_ids=tuple(
                row[
                    SESSION_ROW_ID
                ]
                for row in rows
            ),
            current_total=(
                current_total
            ),
            percentage_total=sum(
                normalized.values(),
                ZERO,
            ),
            items=tuple(
                items
            ),
        )

    def apply(
        self,
        *,
        dimension: str,
        percentages,
        scope_columns=(),
        scope_values=(),
    ) -> DimensionAllocationPreview:
        preview = self.preview(
            dimension=dimension,
            percentages=percentages,
            scope_columns=scope_columns,
            scope_values=scope_values,
        )

        rows = {
            row_id:
                self._workspace
                .get_row(
                    row_id
                )
            for row_id
            in preview.row_ids
        }

        groups = {}

        for item in preview.items:
            groups[item.value] = [
                rows[row_id]
                for row_id
                in item.row_ids
            ]

        replacements = {}

        for item in preview.items:
            group_rows = groups[
                item.value
            ]

            cells = []

            for row in group_rows:
                row_id = row[
                    SESSION_ROW_ID
                ]

                for month in (
                    self._config
                    .month_columns
                ):
                    value = row.get(
                        month
                    )

                    if value is None:
                        continue

                    amount = (
                        self._decimal(
                            value
                        )
                    )

                    if amount < ZERO:
                        raise DimensionAllocationError(
                            "No se puede distribuir "
                            "un conjunto que contiene "
                            "importes negativos."
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

            try:
                allocated = (
                    ProportionalAllocationService
                    .allocate(
                        cells,
                        item.target_total,
                    )
                )

            except ProportionalAllocationError as exc:
                raise DimensionAllocationError(
                    str(exc)
                ) from exc

            for row in group_rows:
                row_id = row[
                    SESSION_ROW_ID
                ]

                updated = deepcopy(
                    row
                )

                for month in (
                    self._config
                    .month_columns
                ):
                    key = (
                        row_id,
                        month,
                    )

                    if key in allocated:
                        updated[
                            month
                        ] = allocated[
                            key
                        ]

                updated[
                    self._config
                    .annual_column
                ] = self._row_month_total(
                    updated
                )

                replacements[
                    row_id
                ] = updated

        description = (
            "Distribuir por "
            f"{dimension}"
        )

        if preview.scope_columns:
            description += (
                " | "
                + " / ".join(
                    f"{column}={value}"
                    for column, value
                    in zip(
                        preview.scope_columns,
                        preview.scope_values,
                    )
                )
            )

        description += (
            " | total="
            f"{preview.current_total}"
        )

        self._workspace.apply_batch(
            description=description,
            replacements=replacements,
        )

        return preview

    def _validate_dimension(
        self,
        dimension,
    ):
        if (
            dimension
            not in self._config
            .groupable_columns
        ):
            raise DimensionAllocationError(
                f"La dimension {dimension} "
                "no pertenece al modulo activo."
            )

        if (
            dimension
            == self._config
            .ceco_column
        ):
            if not (
                self._config
                .capabilities
                .ceco_distribution
            ):
                raise DimensionAllocationError(
                    "El modulo activo no permite "
                    "distribucion por CECO."
                )

            return

        if (
            dimension
            == self._config
            .country_column
        ):
            if not (
                self._config
                .capabilities
                .country_distribution
            ):
                raise DimensionAllocationError(
                    "El modulo activo no permite "
                    "distribucion por pais."
                )

            return

        raise DimensionAllocationError(
            f"La dimension {dimension} "
            "no esta habilitada para "
            "distribucion presupuestal."
        )

    def _validate_scope(
        self,
        dimension,
        columns,
        values,
    ):
        if len(columns) != len(
            values
        ):
            raise DimensionAllocationError(
                "Las dimensiones del alcance "
                "y sus valores no coinciden."
            )

        if (
            len(columns)
            > self.MAX_SCOPE_COLUMNS
        ):
            raise DimensionAllocationError(
                "Solo se permiten hasta "
                f"{self.MAX_SCOPE_COLUMNS} "
                "dimensiones de alcance."
            )

        if len(columns) != len(
            set(columns)
        ):
            raise DimensionAllocationError(
                "No se puede repetir una "
                "dimension del alcance."
            )

        if dimension in columns:
            raise DimensionAllocationError(
                "La dimension que se distribuye "
                "no puede formar parte del "
                "alcance fijo."
            )

        invalid = [
            column
            for column in columns
            if (
                column
                not in self._config
                .groupable_columns
            )
        ]

        if invalid:
            raise DimensionAllocationError(
                "Dimensiones de alcance "
                "no validas: "
                + ", ".join(
                    invalid
                )
            )

    def _find_rows(
        self,
        columns,
        values,
    ):
        rows = []

        for row in (
            self._workspace
            .iter_rows()
        ):
            if not bool(
                row.get(
                    HABILITADO_COLUMN,
                    True,
                )
            ):
                continue

            matches = all(
                row.get(column)
                == value
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

    def _group_rows(
        self,
        rows,
        dimension,
    ):
        groups = {}

        for row in rows:
            value = row.get(
                dimension
            )

            if (
                value is None
                or
                (
                    isinstance(
                        value,
                        str,
                    )
                    and
                    not value.strip()
                )
            ):
                raise DimensionAllocationError(
                    f"La dimension {dimension} "
                    "contiene valores vacios."
                )

            groups.setdefault(
                value,
                [],
            ).append(
                row
            )

        return groups

    def _current_percentages(
        self,
        groups,
    ):
        totals = {
            value: sum(
                (
                    self._annual_amount(
                        row
                    )
                    for row
                    in rows
                ),
                ZERO,
            )
            for value, rows
            in groups.items()
        }

        total = sum(
            totals.values(),
            ZERO,
        )

        if total != ZERO:
            try:
                return (
                    ProportionalAllocationService
                    .allocate(
                        totals.items(),
                        HUNDRED,
                    )
                )

            except ProportionalAllocationError as exc:
                raise DimensionAllocationError(
                    str(exc)
                ) from exc

        keys = list(
            groups
        )

        if not keys:
            return {}

        base = (
            HUNDRED
            / Decimal(
                len(keys)
            )
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        result = {
            key: base
            for key in keys
        }

        residual = (
            HUNDRED
            - sum(
                result.values(),
                ZERO,
            )
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        result[
            keys[-1]
        ] += residual

        return result

    def _validate_percentages(
        self,
        groups,
        percentages,
    ):
        try:
            supplied = dict(
                percentages
            )

        except Exception as exc:
            raise DimensionAllocationError(
                "Los porcentajes no tienen "
                "un formato valido."
            ) from exc

        expected = set(
            groups
        )

        received = set(
            supplied
        )

        missing = (
            expected
            - received
        )

        extra = (
            received
            - expected
        )

        if missing:
            raise DimensionAllocationError(
                "Faltan porcentajes para: "
                + ", ".join(
                    str(value)
                    for value
                    in missing
                )
            )

        if extra:
            raise DimensionAllocationError(
                "Se recibieron valores que "
                "no existen en el alcance: "
                + ", ".join(
                    str(value)
                    for value
                    in extra
                )
            )

        normalized = {}

        for value in groups:
            percentage = (
                self._percentage(
                    supplied[value]
                )
            )

            if percentage < ZERO:
                raise DimensionAllocationError(
                    "Los porcentajes no "
                    "pueden ser negativos."
                )

            normalized[value] = (
                percentage
            )

        total = sum(
            normalized.values(),
            ZERO,
        )

        if total != HUNDRED:
            difference = (
                HUNDRED
                - total
            )

            if difference > ZERO:
                raise DimensionAllocationError(
                    "La distribucion suma "
                    f"{total}% y debe sumar "
                    "100%. Falta "
                    f"{difference}%."
                )

            raise DimensionAllocationError(
                "La distribucion suma "
                f"{total}% y debe sumar "
                "100%. Existe un exceso de "
                f"{abs(difference)}%."
            )

        return normalized

    def _validate_group_basis(
        self,
        rows,
        target,
    ):
        basis = ZERO

        for row in rows:
            for month in (
                self._config
                .month_columns
            ):
                value = row.get(
                    month
                )

                if value is None:
                    continue

                amount = (
                    self._decimal(
                        value
                    )
                )

                if amount < ZERO:
                    raise DimensionAllocationError(
                        "No se puede distribuir "
                        "un conjunto que contiene "
                        "importes negativos."
                    )

                basis += amount

        if (
            target > ZERO
            and
            basis == ZERO
        ):
            raise DimensionAllocationError(
                "Uno de los valores de la "
                "dimension no tiene una "
                "distribucion mensual previa "
                "para recibir presupuesto."
            )

    def _annual_amount(
        self,
        row,
    ):
        amount = self._decimal(
            row.get(
                self._config
                .annual_column
            )
        )

        if amount < ZERO:
            raise DimensionAllocationError(
                "No se puede distribuir "
                "presupuesto con importes "
                "anuales negativos."
            )

        return amount

    def _row_month_total(
        self,
        row,
    ):
        return sum(
            (
                self._decimal(
                    row.get(month)
                )
                for month
                in self._config
                .month_columns
                if row.get(month)
                is not None
            ),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    @staticmethod
    def _decimal(
        value,
    ) -> Decimal:
        if value is None:
            return ZERO

        if isinstance(
            value,
            bool,
        ):
            raise DimensionAllocationError(
                "El importe debe ser numerico."
            )

        if isinstance(
            value,
            Decimal,
        ):
            return value

        try:
            return Decimal(
                str(value)
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise DimensionAllocationError(
                "El importe debe ser numerico."
            ) from exc

    @staticmethod
    def _percentage(
        value,
    ) -> Decimal:
        if isinstance(
            value,
            bool,
        ):
            raise DimensionAllocationError(
                "El porcentaje debe "
                "ser numerico."
            )

        try:
            return Decimal(
                str(value)
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise DimensionAllocationError(
                "El porcentaje debe "
                "ser numerico."
            ) from exc
