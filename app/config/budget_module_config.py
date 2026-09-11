
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
    persistence: bool = True


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

    country_column: str | None = None
    budgeter_column: str | None = None
    ceco_column: str | None = None

    change_detail_columns: tuple[
        str,
        ...
    ] = ()

    insert_column_types: tuple[
        tuple[
            str,
            str,
        ],
        ...
    ] = ()

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
        insert_columns = (
            self.insert_columns
        )

        if insert_columns:
            return insert_columns

        return self.amount_columns

    @property
    def insert_columns(
        self,
    ) -> tuple[
        str,
        ...
    ]:
        return tuple(
            column
            for column, _
            in self.insert_column_types
        )

    @property
    def insert_type_map(
        self,
    ) -> dict[
        str,
        str,
    ]:
        return dict(
            self.insert_column_types
        )
