
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


ZERO = Decimal("0")


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetSummaryDefinition:
    name: str
    module: str

    group_by: tuple[
        str,
        ...
    ]

    amount_column: str

    def __post_init__(
        self,
    ):
        name = str(
            self.name
        ).strip()

        module = str(
            self.module
        ).strip().upper()

        amount_column = str(
            self.amount_column
        ).strip()

        group_by = tuple(
            str(column).strip()
            for column
            in self.group_by
        )

        if not name:
            raise ValueError(
                "name no puede estar vacio."
            )

        if not module:
            raise ValueError(
                "module no puede estar vacio."
            )

        if not amount_column:
            raise ValueError(
                "amount_column no puede "
                "estar vacio."
            )

        if not group_by:
            raise ValueError(
                "group_by debe contener "
                "al menos una columna."
            )

        if any(
            not column
            for column in group_by
        ):
            raise ValueError(
                "group_by contiene una "
                "columna vacia."
            )

        if (
            len(group_by)
            != len(
                set(group_by)
            )
        ):
            raise ValueError(
                "group_by contiene "
                "columnas duplicadas."
            )

        object.__setattr__(
            self,
            "name",
            name,
        )

        object.__setattr__(
            self,
            "module",
            module,
        )

        object.__setattr__(
            self,
            "group_by",
            group_by,
        )

        object.__setattr__(
            self,
            "amount_column",
            amount_column,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetSummaryRow:
    summary_key: str

    dimensions: tuple[
        tuple[
            str,
            Any,
        ],
        ...
    ]

    registros_origen: int
    total_usd: Decimal

    def dimension_dict(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return dict(
            self.dimensions
        )

    def as_dict(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return {
            "summary_key":
                self.summary_key,
            **self.dimension_dict(),
            "registros_origen":
                self.registros_origen,
            "total_usd":
                self.total_usd,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetSummaryResult:
    definition: BudgetSummaryDefinition

    rows: tuple[
        BudgetSummaryRow,
        ...
    ]

    source_row_count: int
    source_total_usd: Decimal

    @property
    def grouped_row_count(
        self,
    ) -> int:
        return len(
            self.rows
        )

    @property
    def summarized_row_count(
        self,
    ) -> int:
        return sum(
            row.registros_origen
            for row in self.rows
        )

    @property
    def summary_total_usd(
        self,
    ) -> Decimal:
        return sum(
            (
                row.total_usd
                for row in self.rows
            ),
            ZERO,
        )

    @property
    def difference_usd(
        self,
    ) -> Decimal:
        return (
            self.summary_total_usd
            - self.source_total_usd
        )

    @property
    def rows_balanced(
        self,
    ) -> bool:
        return (
            self.summarized_row_count
            == self.source_row_count
        )

    @property
    def amounts_balanced(
        self,
    ) -> bool:
        return (
            self.difference_usd
            == ZERO
        )

    @property
    def is_balanced(
        self,
    ) -> bool:
        return (
            self.rows_balanced
            and self.amounts_balanced
        )
