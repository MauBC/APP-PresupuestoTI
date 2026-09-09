from dataclasses import dataclass
from enum import Enum
from typing import Any


class CapexIssueSeverity(
    str,
    Enum,
):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(
    frozen=True,
    slots=True,
)
class CapexImportIssue:
    row_number: int
    column: str
    code: str
    message: str
    severity: CapexIssueSeverity
    raw_value: Any = None


@dataclass(
    frozen=True,
    slots=True,
)
class CapexCleanRowResult:
    row: dict[str, Any]
    issues: tuple[
        CapexImportIssue,
        ...
    ]

    @property
    def errors(
        self,
    ) -> tuple[
        CapexImportIssue,
        ...
    ]:
        return tuple(
            issue
            for issue in self.issues
            if (
                issue.severity
                == CapexIssueSeverity.ERROR
            )
        )

    @property
    def warnings(
        self,
    ) -> tuple[
        CapexImportIssue,
        ...
    ]:
        return tuple(
            issue
            for issue in self.issues
            if (
                issue.severity
                == CapexIssueSeverity.WARNING
            )
        )

    @property
    def is_valid(
        self,
    ) -> bool:
        return not self.errors
