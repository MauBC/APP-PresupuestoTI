from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class UsdAllocationError(ValueError):
    pass


class UsdAllocationService:
    @staticmethod
    def to_decimal(value) -> Decimal:
        if value is None:
            return ZERO

        if isinstance(value, Decimal):
            result = value
        else:
            result = Decimal(str(value))

        return result.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def calculate_total(
        cls,
        row: dict,
    ) -> Decimal:
        total = ZERO

        for column in USD_MONTH_COLUMNS:
            value = row.get(column)

            if value is None:
                continue

            total += cls.to_decimal(value)

        return total.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def set_month(
        cls,
        row: dict,
        column: str,
        value,
    ) -> dict:
        if column not in USD_MONTH_COLUMNS:
            raise UsdAllocationError(
                f"La columna {column} no es "
                "un mes USD editable."
            )

        new_value = cls.to_decimal(value)

        if new_value < ZERO:
            raise UsdAllocationError(
                "No se permiten importes USD negativos."
            )

        result = dict(row)

        result[column] = new_value
        result["anio_usd"] = cls.calculate_total(
            result
        )

        return result

    @classmethod
    def set_annual_total(
        cls,
        row: dict,
        new_total,
    ) -> dict:
        target = cls.to_decimal(new_total)

        if target < ZERO:
            raise UsdAllocationError(
                "No se permiten importes USD negativos."
            )

        current_total = cls.calculate_total(row)

        if current_total == ZERO:
            if target == ZERO:
                return cls._set_existing_months_to_zero(
                    row
                )

            raise UsdAllocationError(
                "No se puede redistribuir un total "
                "distinto de cero porque la suma "
                "actual de los meses es cero."
            )

        factor = target / current_total

        result = dict(row)

        editable_columns = [
            column
            for column in USD_MONTH_COLUMNS
            if row.get(column) is not None
        ]

        if not editable_columns:
            raise UsdAllocationError(
                "La fila no contiene meses USD "
                "disponibles para redistribuir."
            )

        original_values = {
            column: cls.to_decimal(
                row.get(column)
            )
            for column in editable_columns
        }

        for column in editable_columns:
            scaled = (
                original_values[column]
                * factor
            )

            result[column] = scaled.quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

        calculated = cls.calculate_total(
            result
        )

        residual = (
            target - calculated
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if residual != ZERO:
            correction_column = max(
                editable_columns,
                key=lambda column: abs(
                    original_values[column]
                ),
            )

            result[correction_column] = (
                cls.to_decimal(
                    result[correction_column]
                )
                + residual
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

        result["anio_usd"] = target

        return result

    @classmethod
    def _set_existing_months_to_zero(
        cls,
        row: dict,
    ) -> dict:
        result = dict(row)

        for column in USD_MONTH_COLUMNS:
            if row.get(column) is not None:
                result[column] = ZERO

        result["anio_usd"] = ZERO

        return result