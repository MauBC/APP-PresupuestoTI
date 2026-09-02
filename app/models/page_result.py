from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PageResult:
    rows: tuple[dict[str, Any], ...]
    columns: tuple[str, ...]
    total_rows: int
    page_index: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.total_rows == 0:
            return 1

        return (
            self.total_rows
            + self.page_size
            - 1
        ) // self.page_size