from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from app.config.presupuesto_schema import (
    MONTHS,
)
from app.models.opex_smart_enrichment import (
    OpexSmartEnrichedRow,
)
from app.models.opex_smart_periodization import (
    OpexSmartPeriodizedRow,
)
CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class OpexSmartPeriodizationError(
    ValueError
):
    pass


class OpexSmartPeriodizationService:
    @staticmethod
    def _money(
        value,
        *,
        label,
    ) -> Decimal:
        if isinstance(
            value,
            bool,
        ):
            raise OpexSmartPeriodizationError(
                f"{label} debe ser numerico."
            )

        try:
            result = (
                value
                if isinstance(
                    value,
                    Decimal,
                )
                else Decimal(
                    str(value).strip()
                )
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise OpexSmartPeriodizationError(
                f"{label} debe ser numerico."
            ) from exc

        if not result.is_finite():
            raise OpexSmartPeriodizationError(
                f"{label} debe ser finito."
            )

        result = result.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if result < ZERO:
            raise OpexSmartPeriodizationError(
                f"{label} no puede ser negativo."
            )

        return result

    @staticmethod
    def _tipo(
        value,
    ) -> str:
        tipo = str(
            value
            if value is not None
            else ""
        ).strip().upper()

        if tipo not in {
            "ANUAL",
            "MENSUAL",
        }:
            raise OpexSmartPeriodizationError(
                "TIPO debe ser ANUAL o MENSUAL."
            )

        return tipo

    @classmethod
    def periodize_row(
        cls,
        row: OpexSmartEnrichedRow,
    ) -> OpexSmartPeriodizedRow:
        if not isinstance(
            row,
            OpexSmartEnrichedRow,
        ):
            raise TypeError(
                "row debe ser "
                "OpexSmartEnrichedRow."
            )

        tipo = cls._tipo(
            row.tipo
        )

        amount = cls._money(
            row.monto_ceco,
            label="Monto CECO",
        )

        if tipo == "MENSUAL":
            monthly_amounts = tuple(
                (
                    month,
                    amount,
                )
                for month
                in MONTHS
            )

            annual_amount = (
                amount
                * Decimal(
                    len(MONTHS)
                )
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

            return (
                OpexSmartPeriodizedRow(
                    source_row=row,
                    monthly_amounts=(
                        monthly_amounts
                    ),
                    annual_amount=(
                        annual_amount
                    ),
                )
            )

        month_count = len(
            MONTHS
        )

        total_cents = int(
            (
                amount
                * Decimal("100")
            ).to_integral_value()
        )

        base_cents = (
            total_cents
            // month_count
        )

        residual_cents = (
            total_cents
            % month_count
        )

        monthly_amounts = tuple(
            (
                month,
                (
                    Decimal(
                        base_cents
                        + (
                            1
                            if index
                            < residual_cents
                            else 0
                        )
                    )
                    / Decimal("100")
                ).quantize(
                    CENT,
                    rounding=ROUND_HALF_UP,
                ),
            )
            for index, month
            in enumerate(
                MONTHS
            )
        )

        annual_amount = sum(
            (
                month_amount
                for _month, month_amount
                in monthly_amounts
            ),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if annual_amount != amount:
            raise OpexSmartPeriodizationError(
                "La distribucion anual no "
                "conserva el monto del CECO. "
                f"Esperado={amount}; "
                f"obtenido={annual_amount}."
            )

        return (
            OpexSmartPeriodizedRow(
                source_row=row,
                monthly_amounts=(
                    monthly_amounts
                ),
                annual_amount=(
                    annual_amount
                ),
            )
        )

    @classmethod
    def periodize_rows(
        cls,
        rows,
    ) -> tuple[
        OpexSmartPeriodizedRow,
        ...,
    ]:
        try:
            supplied = tuple(
                rows
            )

        except Exception as exc:
            raise OpexSmartPeriodizationError(
                "Las filas OPEX no tienen "
                "un formato valido."
            ) from exc

        return tuple(
            cls.periodize_row(
                row
            )
            for row
            in supplied
        )
