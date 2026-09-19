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
        quantum=CENT,
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

        if result < ZERO:
            raise OpexSmartPeriodizationError(
                f"{label} no puede ser negativo."
            )

        result = result.quantize(
            quantum,
            rounding=ROUND_HALF_UP,
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
        *,
        quantum=CENT,
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
            quantum=quantum,
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
                quantum,
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

        total_units = int(
            (
                amount
                / quantum
            ).to_integral_value()
        )

        base_units = (
            total_units
            // month_count
        )

        residual_units = (
            total_units
            % month_count
        )

        monthly_amounts = tuple(
            (
                month,
                (
                    Decimal(
                        base_units
                        + (
                            1
                            if index
                            < residual_units
                            else 0
                        )
                    )
                    * quantum
                ).quantize(
                    quantum,
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
            quantum,
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
        *,
        quantum=CENT,
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
                row,
                quantum=quantum,
            )
            for row
            in supplied
        )
