from dataclasses import dataclass
from decimal import Decimal


@dataclass(
    frozen=True,
    slots=True,
)
class OpexFxTable:
    year: int
    currency_per_usd: dict[
        str,
        Decimal,
    ]
    local_currency_by_country: dict[
        str,
        str,
    ]
