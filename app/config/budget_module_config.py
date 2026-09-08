from dataclasses import dataclass
from enum import Enum


class BudgetModule(
    str,
    Enum,
):
    OPEX = "OPEX"
    CAPEX = "CAPEX"


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetModuleCapabilities:
    monthly_distribution: bool = True
    ceco_distribution: bool = False
    country_distribution: bool = False
    grouped_editing: bool = True


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetModuleConfig:
    module: BudgetModule
    label: str
    main_table: str

    dimension_columns: tuple[
        str,
        ...
    ]

    groupable_columns: tuple[
        str,
        ...
    ]

    month_columns: tuple[
        str,
        ...
    ]

    annual_column: str

    capabilities: BudgetModuleCapabilities

    configured: bool = True

    @property
    def amount_columns(
        self,
    ) -> tuple[
        str,
        ...
    ]:
        return (
            *self.month_columns,
            self.annual_column,
        )

    @property
    def editable_columns(
        self,
    ) -> tuple[
        str,
        ...
    ]:
        return self.amount_columns
