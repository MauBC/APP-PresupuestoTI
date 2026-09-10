
from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class SharePointDesiredItem:
    summary_key: str

    fields: tuple[
        tuple[str, Any],
        ...
    ]

    def fields_dict(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return dict(
            self.fields
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SharePointCreateAction:
    summary_key: str

    fields: tuple[
        tuple[str, Any],
        ...
    ]

    def fields_dict(
        self,
    ):
        return dict(
            self.fields
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SharePointUpdateAction:
    item_id: str
    summary_key: str

    fields: tuple[
        tuple[str, Any],
        ...
    ]

    etag: str | None = None

    def fields_dict(
        self,
    ):
        return dict(
            self.fields
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SharePointDeleteAction:
    item_id: str
    summary_key: str
    etag: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class SharePointSummarySyncPlan:
    creates: tuple[
        SharePointCreateAction,
        ...
    ]

    updates: tuple[
        SharePointUpdateAction,
        ...
    ]

    deletes: tuple[
        SharePointDeleteAction,
        ...
    ]

    unchanged_keys: tuple[
        str,
        ...
    ]

    unmanaged_item_ids: tuple[
        str,
        ...
    ]

    current_item_count: int
    desired_item_count: int

    @property
    def create_count(
        self,
    ) -> int:
        return len(
            self.creates
        )

    @property
    def update_count(
        self,
    ) -> int:
        return len(
            self.updates
        )

    @property
    def delete_count(
        self,
    ) -> int:
        return len(
            self.deletes
        )

    @property
    def unchanged_count(
        self,
    ) -> int:
        return len(
            self.unchanged_keys
        )

    @property
    def unmanaged_count(
        self,
    ) -> int:
        return len(
            self.unmanaged_item_ids
        )

    @property
    def write_count(
        self,
    ) -> int:
        return (
            self.create_count
            + self.update_count
            + self.delete_count
        )
