
from dataclasses import dataclass
from enum import Enum
from typing import Any


class BudgetImportIssueSeverity(
    str,
    Enum,
):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetImportIssue:
    row_number: int
    column: str
    code: str
    message: str
    severity: BudgetImportIssueSeverity
    raw_value: Any = None
    context: str = ""
    expected_value: Any = None


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetExcelImportResult:
    module: str
    source_path: str
    sheet_name: str
    rows_read: int
    source_column_count: int

    rows: tuple[
        dict[str, Any],
        ...
    ]

    issues: tuple[
        BudgetImportIssue,
        ...
    ] = ()

    source_row_numbers: tuple[
        int,
        ...
    ] = ()

    ignored_row_count: int = 0

    @property
    def error_count(
        self,
    ) -> int:
        return sum(
            1
            for issue in self.issues
            if (
                issue.severity
                == BudgetImportIssueSeverity.ERROR
            )
        )

    @property
    def warning_count(
        self,
    ) -> int:
        return sum(
            1
            for issue in self.issues
            if (
                issue.severity
                == BudgetImportIssueSeverity.WARNING
            )
        )

    @property
    def info_count(
        self,
    ) -> int:
        return sum(
            1
            for issue in self.issues
            if (
                issue.severity
                == BudgetImportIssueSeverity.INFO
            )
        )

    @property
    def importable_count(
        self,
    ) -> int:
        return len(
            self.rows
        )

    @property
    def is_valid(
        self,
    ) -> bool:
        return (
            self.rows_read > 0
            and self.error_count == 0
            and self.importable_count
            == self.rows_read
        )
