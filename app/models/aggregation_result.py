from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AggregationResult:
    rows: tuple[dict[str, Any], ...]
    columns: tuple[str, ...]
    group_columns: tuple[str, ...]