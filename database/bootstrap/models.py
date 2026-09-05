from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CleaningIssue:
    row_number: int
    column: str
    value: Any
    message: str


@dataclass(frozen=True)
class CleaningStats:
    row_count: int
    column_count: int
    amount_count: int
    dash_count: int
    empty_amount_count: int
    error_count: int


@dataclass
class CleaningResult:
    dataframe: pd.DataFrame
    issues: tuple[CleaningIssue, ...]
    extra_columns: tuple[str, ...]
    stats: CleaningStats

    @property
    def is_valid(self) -> bool:
        return not self.issues