from dataclasses import dataclass
from decimal import Decimal

from app.models.opex_smart_enrichment import (
    OpexSmartEnrichedRow,
)


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartPeriodizedRow:
    source_row: OpexSmartEnrichedRow
    monthly_amounts: tuple[
        tuple[str, Decimal],
        ...,
    ]
    annual_amount: Decimal

    def monthly_map(
        self,
    ) -> dict[str, Decimal]:
        return dict(
            self.monthly_amounts
        )
