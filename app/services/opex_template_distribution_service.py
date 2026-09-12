from dataclasses import dataclass
from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from app.models.opex_smart_template import (
    OpexTemplateBudget,
)
from app.services.proportional_allocation_service import (
    ProportionalAllocationError,
    ProportionalAllocationService,
)


CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")


class OpexTemplateDistributionError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class OpexTemplateDistributionStatus:
    percentage_total: Decimal | None
    amount_total: Decimal | None
    target_amount: Decimal
    percentage_difference: Decimal | None
    amount_difference: Decimal | None
    percentage_valid: bool
    amount_valid: bool
    available_modes: tuple[str, ...]

    @property
    def requires_correction(
        self,
    ) -> bool:
        return not (
            self.percentage_valid
            or self.amount_valid
        )

    @property
    def requires_mode_selection(
        self,
    ) -> bool:
        return (
            len(
                self.available_modes
            )
            > 1
        )


@dataclass(
    frozen=True,
    slots=True,
)
class OpexTemplateResolvedDistribution:
    mode: str
    amounts: tuple[
        tuple[str, Decimal],
        ...,
    ]

    @property
    def total(
        self,
    ) -> Decimal:
        return sum(
            (
                amount
                for _, amount
                in self.amounts
            ),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    def amount_map(
        self,
    ) -> dict[str, Decimal]:
        return dict(
            self.amounts
        )


class OpexTemplateDistributionService:
    @staticmethod
    def _decimal(
        value,
        *,
        label,
    ) -> Decimal:
        if isinstance(
            value,
            bool,
        ):
            raise OpexTemplateDistributionError(
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
            raise OpexTemplateDistributionError(
                f"{label} debe ser numerico."
            ) from exc

        if not result.is_finite():
            raise OpexTemplateDistributionError(
                f"{label} debe ser finito."
            )

        return result

    @classmethod
    def inspect(
        cls,
        budget: OpexTemplateBudget,
    ) -> OpexTemplateDistributionStatus:
        percentages = tuple(
            item.percentage
            for item
            in budget.distributions
        )

        amounts = tuple(
            item.amount
            for item
            in budget.distributions
        )

        has_all_percentages = all(
            value is not None
            for value in percentages
        )

        has_all_amounts = all(
            value is not None
            for value in amounts
        )

        percentage_total = (
            sum(
                (
                    value
                    for value
                    in percentages
                    if value is not None
                ),
                Decimal("0"),
            )
            if any(
                value is not None
                for value in percentages
            )
            else None
        )

        amount_total = (
            sum(
                (
                    value
                    for value
                    in amounts
                    if value is not None
                ),
                Decimal("0"),
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )
            if any(
                value is not None
                for value in amounts
            )
            else None
        )

        percentage_difference = (
            (
                Decimal("1")
                - percentage_total
            )
            if percentage_total
            is not None
            else None
        )

        target = (
            cls._decimal(
                budget.monto,
                label="MONTO",
            )
            .quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )
        )

        amount_difference = (
            (
                target
                - amount_total
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )
            if amount_total
            is not None
            else None
        )

        percentage_valid = (
            has_all_percentages
            and
            percentage_total
            == Decimal("1")
        )

        amount_valid = (
            has_all_amounts
            and
            amount_total
            == target
        )

        modes = []

        if any(
            value is not None
            for value in percentages
        ):
            modes.append(
                "PORCENTAJE"
            )

        if any(
            value is not None
            for value in amounts
        ):
            modes.append(
                "IMPORTE"
            )

        return (
            OpexTemplateDistributionStatus(
                percentage_total=(
                    percentage_total
                ),
                amount_total=amount_total,
                target_amount=target,
                percentage_difference=(
                    percentage_difference
                ),
                amount_difference=(
                    amount_difference
                ),
                percentage_valid=(
                    percentage_valid
                ),
                amount_valid=amount_valid,
                available_modes=tuple(
                    modes
                ),
            )
        )

    @staticmethod
    def _expected_cecos(
        budget,
    ):
        return tuple(
            item.ceco
            for item
            in budget.distributions
        )

    @classmethod
    def _validate_keys(
        cls,
        budget,
        values,
    ):
        expected = set(
            cls._expected_cecos(
                budget
            )
        )

        received = set(
            values
        )

        missing = sorted(
            expected
            - received
        )

        extra = sorted(
            received
            - expected
        )

        if missing:
            raise OpexTemplateDistributionError(
                "Faltan CECO en la distribucion: "
                + ", ".join(
                    missing
                )
            )

        if extra:
            raise OpexTemplateDistributionError(
                "Existen CECO no esperados: "
                + ", ".join(
                    extra
                )
            )

    @classmethod
    def resolve_percentages(
        cls,
        budget: OpexTemplateBudget,
        percentages,
    ) -> OpexTemplateResolvedDistribution:
        supplied = dict(
            percentages
        )

        cls._validate_keys(
            budget,
            supplied,
        )

        normalized = {}

        for ceco in (
            cls._expected_cecos(
                budget
            )
        ):
            percentage = cls._decimal(
                supplied[ceco],
                label=(
                    f"Porcentaje de {ceco}"
                ),
            )

            if (
                percentage < ZERO
                or
                percentage > HUNDRED
            ):
                raise OpexTemplateDistributionError(
                    "Cada porcentaje debe estar "
                    "entre 0 y 100."
                )

            normalized[
                ceco
            ] = percentage

        total = sum(
            normalized.values(),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if total != HUNDRED:
            difference = (
                HUNDRED
                - total
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

            if difference > ZERO:
                raise OpexTemplateDistributionError(
                    "La distribucion suma "
                    f"{total}% y debe sumar "
                    "100%. Falta "
                    f"{difference}%."
                )

            raise OpexTemplateDistributionError(
                "La distribucion suma "
                f"{total}% y debe sumar "
                "100%. Existe un exceso de "
                f"{abs(difference)}%."
            )

        try:
            allocated = (
                ProportionalAllocationService
                .allocate(
                    normalized.items(),
                    budget.monto,
                )
            )

        except ProportionalAllocationError as exc:
            raise OpexTemplateDistributionError(
                str(exc)
            ) from exc

        return (
            OpexTemplateResolvedDistribution(
                mode="PORCENTAJE",
                amounts=tuple(
                    (
                        ceco,
                        allocated[ceco],
                    )
                    for ceco
                    in cls._expected_cecos(
                        budget
                    )
                ),
            )
        )

    @classmethod
    def resolve_amounts(
        cls,
        budget: OpexTemplateBudget,
        amounts,
    ) -> OpexTemplateResolvedDistribution:
        supplied = dict(
            amounts
        )

        cls._validate_keys(
            budget,
            supplied,
        )

        normalized = {}

        for ceco in (
            cls._expected_cecos(
                budget
            )
        ):
            amount = (
                cls._decimal(
                    supplied[ceco],
                    label=(
                        f"Importe de {ceco}"
                    ),
                )
                .quantize(
                    CENT,
                    rounding=ROUND_HALF_UP,
                )
            )

            if amount < ZERO:
                raise OpexTemplateDistributionError(
                    "Los importes no pueden "
                    "ser negativos."
                )

            normalized[
                ceco
            ] = amount

        total = sum(
            normalized.values(),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        target = (
            cls._decimal(
                budget.monto,
                label="MONTO",
            )
            .quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )
        )

        if total != target:
            difference = (
                target
                - total
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

            raise OpexTemplateDistributionError(
                "La suma de importes es "
                f"{total:,.2f} y MONTO es "
                f"{target:,.2f}. "
                "Diferencia: "
                f"{difference:,.2f}."
            )

        return (
            OpexTemplateResolvedDistribution(
                mode="IMPORTE",
                amounts=tuple(
                    (
                        ceco,
                        normalized[ceco],
                    )
                    for ceco
                    in cls._expected_cecos(
                        budget
                    )
                ),
            )
        )

    @classmethod
    def rebalance_amounts(
        cls,
        budget: OpexTemplateBudget,
        amounts,
    ) -> OpexTemplateResolvedDistribution:
        supplied = dict(
            amounts
        )

        cls._validate_keys(
            budget,
            supplied,
        )

        normalized = []

        for ceco in (
            cls._expected_cecos(
                budget
            )
        ):
            amount = cls._decimal(
                supplied[ceco],
                label=(
                    f"Importe de {ceco}"
                ),
            )

            if amount < ZERO:
                raise OpexTemplateDistributionError(
                    "Los importes no pueden "
                    "ser negativos."
                )

            normalized.append(
                (
                    ceco,
                    amount,
                )
            )

        try:
            allocated = (
                ProportionalAllocationService
                .allocate(
                    normalized,
                    budget.monto,
                )
            )

        except ProportionalAllocationError as exc:
            raise OpexTemplateDistributionError(
                str(exc)
            ) from exc

        return (
            OpexTemplateResolvedDistribution(
                mode="IMPORTE",
                amounts=tuple(
                    (
                        ceco,
                        allocated[ceco],
                    )
                    for ceco
                    in cls._expected_cecos(
                        budget
                    )
                ),
            )
        )

    @classmethod
    def percentage_inputs(
        cls,
        budget,
    ):
        result = {}

        for item in budget.distributions:
            if item.percentage is None:
                continue

            result[
                item.ceco
            ] = (
                item.percentage
                * Decimal("100")
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

        return result

    @classmethod
    def amount_inputs(
        cls,
        budget,
    ):
        return {
            item.ceco:
                item.amount
            for item
            in budget.distributions
            if item.amount is not None
        }
