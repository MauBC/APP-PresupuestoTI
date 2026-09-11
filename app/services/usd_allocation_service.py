from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)


CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal("100")


class UsdAllocationError(ValueError):
    pass


class UsdAllocationService:
    @staticmethod
    def to_decimal(
        value,
    ) -> Decimal:
        if value is None:
            return ZERO

        if isinstance(value, bool):
            raise UsdAllocationError(
                "El importe debe ser numerico."
            )

        if isinstance(value, Decimal):
            result = value
        else:
            try:
                result = Decimal(
                    str(value)
                )
            except (
                InvalidOperation,
                ValueError,
                TypeError,
            ) as exc:
                raise UsdAllocationError(
                    "El importe debe ser numerico."
                ) from exc

        return result.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    @staticmethod
    def to_percentage(
        value,
    ) -> Decimal:
        if value is None:
            return ZERO

        if isinstance(value, bool):
            raise UsdAllocationError(
                "El porcentaje debe ser numerico."
            )

        if isinstance(value, Decimal):
            return value

        try:
            return Decimal(
                str(value)
            )
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ) as exc:
            raise UsdAllocationError(
                "El porcentaje debe ser numerico."
            ) from exc

    @staticmethod
    def _resolve_month_columns(
        month_columns=None,
    ) -> tuple[str, ...]:
        if month_columns is None:
            columns = (
                OPEX_MODULE_CONFIG
                .month_columns
            )
        else:
            columns = tuple(
                month_columns
            )

        if not columns:
            raise UsdAllocationError(
                "No existen columnas mensuales "
                "configuradas."
            )

        if len(columns) != len(
            set(columns)
        ):
            raise UsdAllocationError(
                "Las columnas mensuales "
                "contienen duplicados."
            )

        return tuple(
            columns
        )

    @staticmethod
    def _resolve_annual_column(
        annual_column=None,
    ) -> str:
        if annual_column is None:
            column = (
                OPEX_MODULE_CONFIG
                .annual_column
            )
        else:
            column = str(
                annual_column
            ).strip()

        if not column:
            raise UsdAllocationError(
                "No existe una columna anual "
                "configurada."
            )

        return column

    @classmethod
    def calculate_total(
        cls,
        row: dict,
        *,
        month_columns=None,
    ) -> Decimal:
        columns = (
            cls._resolve_month_columns(
                month_columns
            )
        )

        total = ZERO

        for column in columns:
            value = row.get(
                column
            )

            if value is None:
                continue

            total += cls.to_decimal(
                value
            )

        return total.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def calculate_percentage_total(
        cls,
        percentages,
        *,
        month_columns=None,
    ) -> Decimal:
        columns = (
            cls._resolve_month_columns(
                month_columns
            )
        )

        percentages = dict(
            percentages
        )

        unknown = (
            set(percentages)
            - set(columns)
        )

        if unknown:
            raise UsdAllocationError(
                "Existen meses no configurados: "
                + ", ".join(
                    sorted(
                        unknown
                    )
                )
            )

        return sum(
            (
                cls.to_percentage(
                    percentages.get(
                        column,
                        ZERO,
                    )
                )
                for column in columns
            ),
            ZERO,
        )

    @classmethod
    def set_month(
        cls,
        row: dict,
        column: str,
        value,
        *,
        month_columns=None,
        annual_column=None,
    ) -> dict:
        columns = (
            cls._resolve_month_columns(
                month_columns
            )
        )

        annual = (
            cls._resolve_annual_column(
                annual_column
            )
        )

        if column not in columns:
            raise UsdAllocationError(
                f"La columna {column} no es "
                "un mes editable."
            )

        if row.get(column) is None:
            raise UsdAllocationError(
                f"El mes {column} no esta "
                "disponible para esta fila."
            )

        new_value = cls.to_decimal(
            value
        )

        if new_value < ZERO:
            raise UsdAllocationError(
                "No se permiten importes "
                "negativos."
            )

        result = dict(
            row
        )

        result[column] = (
            new_value
        )

        result[annual] = (
            cls.calculate_total(
                result,
                month_columns=columns,
            )
        )

        return result

    @classmethod
    def set_annual_total(
        cls,
        row: dict,
        new_total,
        *,
        month_columns=None,
        annual_column=None,
    ) -> dict:
        columns = (
            cls._resolve_month_columns(
                month_columns
            )
        )

        annual = (
            cls._resolve_annual_column(
                annual_column
            )
        )

        target = cls.to_decimal(
            new_total
        )

        if target < ZERO:
            raise UsdAllocationError(
                "No se permiten importes "
                "negativos."
            )

        current_total = (
            cls.calculate_total(
                row,
                month_columns=columns,
            )
        )

        if current_total == ZERO:
            if target == ZERO:
                return (
                    cls._set_existing_months_to_zero(
                        row,
                        month_columns=columns,
                        annual_column=annual,
                    )
                )

            raise UsdAllocationError(
                "No se puede redistribuir un total "
                "distinto de cero porque la suma "
                "actual de los meses es cero."
            )

        editable_columns = [
            column
            for column in columns
            if row.get(column) is not None
        ]

        if not editable_columns:
            raise UsdAllocationError(
                "La fila no contiene meses "
                "disponibles para redistribuir."
            )

        factor = (
            target
            / current_total
        )

        result = dict(
            row
        )

        original_values = {
            column:
                cls.to_decimal(
                    row.get(column)
                )
            for column
            in editable_columns
        }

        for column in (
            editable_columns
        ):
            scaled = (
                original_values[column]
                * factor
            )

            result[column] = (
                scaled.quantize(
                    CENT,
                    rounding=ROUND_HALF_UP,
                )
            )

        calculated = (
            cls.calculate_total(
                result,
                month_columns=columns,
            )
        )

        residual = (
            target
            - calculated
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if residual != ZERO:
            correction_column = max(
                editable_columns,
                key=lambda column: abs(
                    original_values[
                        column
                    ]
                ),
            )

            result[
                correction_column
            ] = (
                cls.to_decimal(
                    result[
                        correction_column
                    ]
                )
                + residual
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

        final_total = (
            cls.calculate_total(
                result,
                month_columns=columns,
            )
        )

        if final_total != target:
            raise UsdAllocationError(
                "No fue posible ajustar "
                "la distribucion mensual "
                "al total anual."
            )

        result[annual] = target

        return result

    @classmethod
    def set_percentage_distribution(
        cls,
        row: dict,
        percentages,
        *,
        total=None,
        month_columns=None,
        annual_column=None,
    ) -> dict:
        columns = (
            cls._resolve_month_columns(
                month_columns
            )
        )

        annual = (
            cls._resolve_annual_column(
                annual_column
            )
        )

        percentages = dict(
            percentages
        )

        unknown = (
            set(percentages)
            - set(columns)
        )

        if unknown:
            raise UsdAllocationError(
                "Existen meses no configurados: "
                + ", ".join(
                    sorted(
                        unknown
                    )
                )
            )

        if total is None:
            target = cls.to_decimal(
                row.get(
                    annual
                )
            )
        else:
            target = cls.to_decimal(
                total
            )

        if target < ZERO:
            raise UsdAllocationError(
                "El presupuesto anual "
                "no puede ser negativo."
            )

        editable_columns = [
            column
            for column in columns
            if row.get(column) is not None
        ]

        if not editable_columns:
            raise UsdAllocationError(
                "La fila no contiene meses "
                "disponibles para distribuir."
            )

        normalized = {}

        for column in columns:
            percentage = (
                cls.to_percentage(
                    percentages.get(
                        column,
                        ZERO,
                    )
                )
            )

            if percentage < ZERO:
                raise UsdAllocationError(
                    "Los porcentajes no pueden "
                    "ser negativos."
                )

            if (
                row.get(column) is None
                and percentage != ZERO
            ):
                raise UsdAllocationError(
                    f"El mes {column} no esta "
                    "disponible para esta fila."
                )

            if column in editable_columns:
                normalized[column] = (
                    percentage
                )

        percentage_total = sum(
            normalized.values(),
            ZERO,
        )

        if percentage_total != HUNDRED:
            difference = (
                HUNDRED
                - percentage_total
            )

            if difference > ZERO:
                raise UsdAllocationError(
                    "La distribucion suma "
                    f"{percentage_total}% "
                    "y debe sumar 100%. "
                    f"Falta {difference}%."
                )

            raise UsdAllocationError(
                "La distribucion suma "
                f"{percentage_total}% "
                "y debe sumar 100%. "
                f"Existe un exceso de "
                f"{abs(difference)}%."
            )

        result = dict(
            row
        )

        for column in (
            editable_columns
        ):
            amount = (
                target
                * normalized[column]
                / HUNDRED
            )

            result[column] = (
                amount.quantize(
                    CENT,
                    rounding=ROUND_HALF_UP,
                )
            )

        calculated = (
            cls.calculate_total(
                result,
                month_columns=columns,
            )
        )

        residual = (
            target
            - calculated
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if residual != ZERO:
            correction_column = max(
                editable_columns,
                key=lambda column:
                    normalized[column],
            )

            result[
                correction_column
            ] = (
                cls.to_decimal(
                    result[
                        correction_column
                    ]
                )
                + residual
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

        final_total = (
            cls.calculate_total(
                result,
                month_columns=columns,
            )
        )

        if final_total != target:
            raise UsdAllocationError(
                "La suma mensual no coincide "
                "con el presupuesto anual."
            )

        result[annual] = target

        return result

    @classmethod
    def _set_existing_months_to_zero(
        cls,
        row: dict,
        *,
        month_columns=None,
        annual_column=None,
    ) -> dict:
        columns = (
            cls._resolve_month_columns(
                month_columns
            )
        )

        annual = (
            cls._resolve_annual_column(
                annual_column
            )
        )

        result = dict(
            row
        )

        for column in columns:
            if row.get(column) is not None:
                result[column] = ZERO

        result[annual] = ZERO

        return result
