from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class DashboardResult:
    total_usd: Decimal
    total_rows: int
    total_countries: int
    total_budgeters: int

    by_country: tuple[dict[str, Any], ...]
    by_budgeter: tuple[dict[str, Any], ...]