from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from app.config.presupuesto_schema import (
    AMOUNT_GROUPS,
    MONTHS,
)
from app.models.opex_fx import (
    OpexFxTable,
)
from app.models.opex_smart_periodization import (
    OpexSmartPeriodizedRow,
)


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class OpexFxError(
    ValueError
):
    pass


class OpexFxService:
    _CURRENCY_ALIASES = {
        "COPS": "COP",
    }

    def __init__(
        self,
        table: OpexFxTable,
    ):
        if not isinstance(
            table,
            OpexFxTable,
        ):
            raise TypeError(
                "table debe ser OpexFxTable."
            )

        if table.year != 2027:
            raise OpexFxError(
                "La tabla FX para insercion "
                "inteligente OPEX debe "
                "corresponder a 2027."
            )

        self._year = table.year

        self._rates = {
            self._currency(
                currency
            ):
                self._positive_rate(
                    rate,
                    currency=currency,
                )
            for (
                currency,
                rate,
            )
            in table
            .currency_per_usd
            .items()
        }

        self._local_currency = {
            self._country(
                country
            ):
                self._currency(
                    currency
                )
            for (
                country,
                currency,
            )
            in table
            .local_currency_by_country
            .items()
        }

        if "USD" not in self._rates:
            raise OpexFxError(
                "La tabla FX debe incluir USD."
            )

        if (
            self._rates["USD"]
            != Decimal("1")
        ):
            raise OpexFxError(
                "La tasa de USD debe ser 1."
            )

    @classmethod
    def _currency(
        cls,
        value,
    ) -> str:
        text = str(
            value
            if value is not None
            else ""
        ).strip().upper()

        if not text:
            raise OpexFxError(
                "La moneda no puede estar vacia."
            )

        return cls._CURRENCY_ALIASES.get(
            text,
            text,
        )

    @staticmethod
    def _country(
        value,
    ) -> str:
        text = str(
            value
            if value is not None
            else ""
        ).strip().upper()

        if not text:
            raise OpexFxError(
                "El pais no puede estar vacio."
            )

        return text

    @staticmethod
    def _positive_rate(
        value,
        *,
        currency,
    ) -> Decimal:
        try:
            rate = (
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
            raise OpexFxError(
                "La tasa FX de "
                f"{currency} debe ser numerica."
            ) from exc

        if (
            not rate.is_finite()
            or rate <= ZERO
        ):
            raise OpexFxError(
                "La tasa FX de "
                f"{currency} debe ser mayor "
                "que cero."
            )

        return rate

    def _rate(
        self,
        currency,
    ) -> Decimal:
        normalized = (
            self._currency(
                currency
            )
        )

        try:
            return self._rates[
                normalized
            ]

        except KeyError as exc:
            raise OpexFxError(
                "No existe TC 2027 "
                f"para {normalized}."
            ) from exc

    def local_currency(
        self,
        country,
    ) -> str:
        normalized = (
            self._country(
                country
            )
        )

        try:
            return self._local_currency[
                normalized
            ]

        except KeyError as exc:
            raise OpexFxError(
                "No existe moneda local "
                f"configurada para {normalized}."
            ) from exc

    @staticmethod
    def _money(
        value,
    ) -> Decimal:
        try:
            result = (
                value
                if isinstance(
                    value,
                    Decimal,
                )
                else Decimal(
                    str(value)
                )
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise OpexFxError(
                "El importe a convertir "
                "debe ser numerico."
            ) from exc

        if (
            not result.is_finite()
            or result < ZERO
        ):
            raise OpexFxError(
                "El importe a convertir "
                "debe ser finito y no negativo."
            )

        return result

    def convert_month(
        self,
        *,
        mf_amount,
        invoice_currency,
        country,
    ):
        mf = self._money(
            mf_amount
        )

        invoice = self._currency(
            invoice_currency
        )

        local = self.local_currency(
            country
        )

        invoice_rate = self._rate(
            invoice
        )

        local_rate = self._rate(
            local
        )

        raw_usd = (
            mf
            / invoice_rate
        )

        usd = raw_usd.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        ml = (
            raw_usd
            * local_rate
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        return {
            "mf":
                mf.quantize(
                    CENT,
                    rounding=ROUND_HALF_UP,
                ),
            "usd":
                usd,
            "ml":
                ml,
        }

    def monthly_values(
        self,
        periodized:
            OpexSmartPeriodizedRow,
    ):
        if not isinstance(
            periodized,
            OpexSmartPeriodizedRow,
        ):
            raise TypeError(
                "periodized debe ser "
                "OpexSmartPeriodizedRow."
            )

        source = (
            periodized.source_row
        )

        enrichment = (
            source.enrichment
        )

        if enrichment is None:
            raise OpexFxError(
                "La fila OPEX no contiene "
                "enriquecimiento para resolver "
                "el pais."
            )

        monthly = (
            periodized.monthly_map()
        )

        result = {}

        for month in MONTHS:
            converted = (
                self.convert_month(
                    mf_amount=(
                        monthly[month]
                    ),
                    invoice_currency=(
                        source
                        .moneda_facturacion
                    ),
                    country=(
                        enrichment.pais
                    ),
                )
            )

            for group in AMOUNT_GROUPS:
                result[
                    f"{month}_{group}"
                ] = converted[
                    group
                ]

        return result
