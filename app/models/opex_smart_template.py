from dataclasses import dataclass
from decimal import Decimal


@dataclass(
    frozen=True,
    slots=True,
)
class OpexTemplateDistribution:
    excel_row: int
    ceco: str
    percentage: Decimal | None
    amount: Decimal | None


@dataclass(
    frozen=True,
    slots=True,
)
class OpexTemplateBudget:
    sheet_name: str

    nombre_gasto: str
    proveedor: str
    moneda_facturacion: str
    numero_cuenta: str

    tipo: str
    monto: Decimal

    distributions: tuple[
        OpexTemplateDistribution,
        ...,
    ]

    @property
    def ceco_count(
        self,
    ) -> int:
        return len(
            self.distributions
        )

    @property
    def total_percentage(
        self,
    ) -> Decimal | None:
        values = tuple(
            item.percentage
            for item
            in self.distributions
            if item.percentage is not None
        )

        if not values:
            return None

        return sum(
            values,
            Decimal("0"),
        )

    @property
    def total_distribution_amount(
        self,
    ) -> Decimal | None:
        values = tuple(
            item.amount
            for item
            in self.distributions
            if item.amount is not None
        )

        if not values:
            return None

        return sum(
            values,
            Decimal("0"),
        )

    @property
    def distribution_mode(
        self,
    ) -> str:
        has_percentage = any(
            item.percentage is not None
            for item
            in self.distributions
        )

        has_amount = any(
            item.amount is not None
            for item
            in self.distributions
        )

        if (
            has_percentage
            and has_amount
        ):
            return "PORCENTAJE+IMPORTE"

        if has_percentage:
            return "PORCENTAJE"

        if has_amount:
            return "IMPORTE"

        return "SIN_DISTRIBUCION"


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartTemplateWorkbook:
    source_path: str

    budgets: tuple[
        OpexTemplateBudget,
        ...,
    ]

    @property
    def budget_count(
        self,
    ) -> int:
        return len(
            self.budgets
        )

    @property
    def generated_row_count(
        self,
    ) -> int:
        return sum(
            budget.ceco_count
            for budget
            in self.budgets
        )
