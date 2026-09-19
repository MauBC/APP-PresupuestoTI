from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class ProportionalAllocationError(
    ValueError
):
    pass


class ProportionalAllocationService:
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
            raise ProportionalAllocationError(
                "El valor debe ser numerico."
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
            raise ProportionalAllocationError(
                "El valor debe ser numerico."
            ) from exc

    @classmethod
    def _target(
        cls,
        value,
        *,
        quantum=CENT,
    ) -> Decimal:
        target = cls._decimal(
            value
        )

        if target < ZERO:
            raise ProportionalAllocationError(
                "El total objetivo no puede "
                "ser negativo."
            )

        return target.quantize(
            quantum,
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def allocate(
        cls,
        values,
        target,
        *,
        quantum=CENT,
    ):
        items = list(
            values
        )

        target_amount = (
            cls._target(
                target,
                quantum=quantum,
            )
        )

        if not items:
            if target_amount == ZERO:
                return {}

            raise ProportionalAllocationError(
                "No existen valores disponibles "
                "para realizar la distribucion."
            )

        normalized = []
        seen = set()

        for key, value in items:
            if key in seen:
                raise ProportionalAllocationError(
                    "La distribucion contiene "
                    "claves duplicadas."
                )

            seen.add(
                key
            )

            amount = cls._decimal(
                value
            )

            if amount < ZERO:
                raise ProportionalAllocationError(
                    "No se pueden redistribuir "
                    "valores negativos."
                )

            normalized.append(
                (
                    key,
                    amount,
                )
            )

        current_total = sum(
            (
                amount
                for _, amount
                in normalized
            ),
            ZERO,
        )

        if (
            current_total == ZERO
            and
            target_amount > ZERO
        ):
            raise ProportionalAllocationError(
                "No existe una distribucion "
                "previa para repartir el "
                "nuevo presupuesto."
            )

        if target_amount == ZERO:
            return {
                key: ZERO.quantize(
                    quantum
                )
                for key, _
                in normalized
            }

        factor = (
            target_amount
            / current_total
        )

        result = {}

        for key, amount in normalized:
            result[key] = (
                amount
                * factor
            ).quantize(
                quantum,
                rounding=ROUND_HALF_UP,
            )

        allocated_total = sum(
            result.values(),
            ZERO,
        )

        residual = (
            target_amount
            - allocated_total
        ).quantize(
            quantum,
            rounding=ROUND_HALF_UP,
        )

        if residual != ZERO:
            correction_key = max(
                normalized,
                key=lambda item: abs(
                    item[1]
                ),
            )[0]

            if result[correction_key] + residual >= ZERO:
                result[correction_key] += residual
            else:
                # Muchos redondeos hacia arriba pueden superar el importe
                # de una sola fila. Descontar solo el saldo disponible en
                # cada fila conserva el total sin crear valores negativos.
                remaining = -residual
                for key, _ in sorted(normalized, key=lambda item: item[1], reverse=True):
                    correction = min(result[key], remaining)
                    result[key] -= correction
                    remaining -= correction
                    if remaining == ZERO:
                        break

        final_total = sum(
            result.values(),
            ZERO,
        ).quantize(
            quantum,
            rounding=ROUND_HALF_UP,
        )

        if final_total != target_amount:
            raise ProportionalAllocationError(
                "No fue posible ajustar la "
                "distribucion al total objetivo."
            )

        return result
