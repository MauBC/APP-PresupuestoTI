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
from app.services.usd_allocation_service import (
    UsdAllocationError,
    UsdAllocationService,
)


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class GroupMonthlyDistributionError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class GroupMonthlyDistributionPreview:
    group_columns: tuple[str, ...]
    group_values: tuple[Any, ...]
    row_ids: tuple[int, ...]
    current_total: Decimal
    target_total: Decimal
    month_totals: tuple[
        tuple[
            str,
            Decimal,
        ],
        ...,
    ]

    @property
    def row_count(
        self,
    ) -> int:
        return len(
            self.row_ids
        )

    @property
    def month_total_map(
        self,
    ) -> dict[
        str,
        Decimal,
    ]:
        return dict(
            self.month_totals
        )


class GroupMonthlyDistributionService:
    MAX_GROUP_COLUMNS = MAX_GROUPING_LEVELS

    def __init__(
        self,
        workspace:
            PresupuestoWorkspace,
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
        percentages,
        annual_total=None,
    ) -> GroupMonthlyDistributionPreview:
        self._ensure_enabled()

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

        rows = self._find_rows(
            columns,
            values,
        )

        if not rows:
            raise GroupMonthlyDistributionError(
                "La agrupacion no contiene "
                "registros habilitados."
            )

        current_total = sum(
            (
                self._row_total(
                    row
                )
                for row in rows
            ),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        target_total = (
            current_total
            if annual_total is None
            else self._amount(
                annual_total
            )
        )

        if (
            target_total > ZERO
            and current_total == ZERO
        ):
            raise GroupMonthlyDistributionError(
                "El grupo no tiene una "
                "distribucion anual previa "
                "distinta de cero. "
                "No es posible repartir un "
                "nuevo total proporcionalmente."
            )

        aggregate_row = {
            month:
                sum(
                    (
                        self._decimal(
                            row.get(
                                month
                            )
                        )
                        for row in rows
                    ),
                    ZERO,
                ).quantize(
                    CENT,
                    rounding=ROUND_HALF_UP,
                )
            for month
            in self._config.month_columns
        }

        aggregate_row[
            self._config
            .annual_column
        ] = current_total

        try:
            distributed = (
                UsdAllocationService
                .set_percentage_distribution(
                    aggregate_row,
                    percentages,
                    total=target_total,
                    month_columns=(
                        self._config
                        .month_columns
                    ),
                    annual_column=(
                        self._config
                        .annual_column
                    ),
                )
            )

        except (
            UsdAllocationError,
            ValueError,
            InvalidOperation,
        ) as exc:
            raise (
                GroupMonthlyDistributionError(
                    str(exc)
                )
            ) from exc

        return (
            GroupMonthlyDistributionPreview(
                group_columns=columns,
                group_values=values,
                row_ids=tuple(
                    row[
                        SESSION_ROW_ID
                    ]
                    for row in rows
                ),
                current_total=(
                    current_total
                ),
                target_total=(
                    target_total
                ),
                month_totals=tuple(
                    (
                        month,
                        self._decimal(
                            distributed[
                                month
                            ]
                        ),
                    )
                    for month
                    in self._config
                    .month_columns
                ),
            )
        )

    def apply(
        self,
        *,
        group_columns,
        group_values,
        percentages,
        annual_total=None,
    ) -> GroupMonthlyDistributionPreview:
        preview = self.preview(
            group_columns=(
                group_columns
            ),
            group_values=(
                group_values
            ),
            percentages=(
                percentages
            ),
            annual_total=(
                annual_total
            ),
        )

        rows = self._find_rows(
            preview.group_columns,
            preview.group_values,
        )

        targets = (
            self._allocate_row_totals(
                rows,
                preview.target_total,
            )
        )

        replacements = {}

        for row in rows:
            row_id = row[
                SESSION_ROW_ID
            ]

            try:
                updated = (
                    UsdAllocationService
                    .set_percentage_distribution(
                        row,
                        percentages,
                        total=(
                            targets[
                                row_id
                            ]
                        ),
                        month_columns=(
                            self._config
                            .month_columns
                        ),
                        annual_column=(
                            self._config
                            .annual_column
                        ),
                    )
                )

            except (
                UsdAllocationError,
                ValueError,
                InvalidOperation,
            ) as exc:
                raise (
                    GroupMonthlyDistributionError(
                        str(exc)
                    )
                ) from exc

            replacements[
                row_id
            ] = updated

        self._workspace.apply_batch(
            description=(
                "Distribuir meses del grupo"
            ),
            replacements=(
                replacements
            ),
        )

        return preview

    def _allocate_row_totals(
        self,
        rows,
        target_total: Decimal,
    ) -> dict[
        int,
        Decimal,
    ]:
        basis = {
            row[
                SESSION_ROW_ID
            ]:
                self._row_total(
                    row
                )
            for row in rows
        }

        basis_total = sum(
            basis.values(),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if target_total == ZERO:
            return {
                row_id: ZERO
                for row_id
                in basis
            }

        if basis_total == ZERO:
            raise GroupMonthlyDistributionError(
                "No existe base anual "
                "para distribuir el grupo."
            )

        result = {}

        for row_id, amount in (
            basis.items()
        ):
            result[row_id] = (
                target_total
                * amount
                / basis_total
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

        residual = (
            target_total
            - sum(
                result.values(),
                ZERO,
            )
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if residual != ZERO:
            correction_row_id = max(
                basis,
                key=lambda row_id:
                    (
                        abs(
                            basis[
                                row_id
                            ]
                        ),
                        -row_id,
                    ),
            )

            result[
                correction_row_id
            ] = (
                result[
                    correction_row_id
                ]
                + residual
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

        if (
            sum(
                result.values(),
                ZERO,
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )
            != target_total
        ):
            raise GroupMonthlyDistributionError(
                "No fue posible ajustar "
                "el total anual del grupo."
            )

        return result

    def _find_rows(
        self,
        columns,
        values,
    ):
        result = []

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

            if all(
                row.get(column)
                == value
                for column, value
                in zip(
                    columns,
                    values,
                )
            ):
                result.append(
                    row
                )

        return result

    def _validate_group(
        self,
        columns,
        values,
    ) -> None:
        if not columns:
            raise GroupMonthlyDistributionError(
                "Debe seleccionar una "
                "agrupacion."
            )

        if (
            len(columns)
            > self.MAX_GROUP_COLUMNS
        ):
            raise GroupMonthlyDistributionError(
                "Solo se permiten hasta "
                f"{self.MAX_GROUP_COLUMNS} "
                "niveles de agrupacion."
            )

        if (
            len(columns)
            != len(values)
        ):
            raise GroupMonthlyDistributionError(
                "Las columnas y valores "
                "del grupo no coinciden."
            )

        if (
            len(columns)
            != len(
                set(
                    columns
                )
            )
        ):
            raise GroupMonthlyDistributionError(
                "No se pueden repetir "
                "columnas de agrupacion."
            )

        invalid = [
            column
            for column in columns
            if column not in (
                self._config
                .groupable_columns
            )
        ]

        if invalid:
            raise GroupMonthlyDistributionError(
                "Columnas de agrupacion "
                "no validas: "
                + ", ".join(
                    invalid
                )
            )

    def _ensure_enabled(
        self,
    ) -> None:
        if not (
            self._config
            .capabilities
            .monthly_distribution
        ):
            raise GroupMonthlyDistributionError(
                "El modulo activo no permite "
                "distribucion mensual."
            )

    def _row_total(
        self,
        row,
    ) -> Decimal:
        return (
            UsdAllocationService
            .calculate_total(
                row,
                month_columns=(
                    self._config
                    .month_columns
                ),
            )
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
    def _amount(
        cls,
        value,
    ) -> Decimal:
        try:
            result = cls._decimal(
                value
            )

        except (
            InvalidOperation,
            ValueError,
        ) as exc:
            raise GroupMonthlyDistributionError(
                "Importe anual no valido."
            ) from exc

        if result < ZERO:
            raise GroupMonthlyDistributionError(
                "El presupuesto anual "
                "no puede ser negativo."
            )

        return result.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )
