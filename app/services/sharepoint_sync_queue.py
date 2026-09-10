
from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class SharePointSyncRequest:
    source_batch_id: str | None = None
    manual: bool = False

    def __post_init__(
        self,
    ):
        value = (
            str(
                self.source_batch_id
            ).strip()
            if self.source_batch_id
            is not None
            else None
        )

        object.__setattr__(
            self,
            "source_batch_id",
            value or None,
        )


class SharePointSyncRequestQueue:
    def __init__(
        self,
    ):
        self._running = False
        self._current = None
        self._pending = None

    @property
    def is_running(
        self,
    ) -> bool:
        return self._running

    @property
    def has_pending(
        self,
    ) -> bool:
        return (
            self._pending
            is not None
        )

    @property
    def current(
        self,
    ):
        return self._current

    def request(
        self,
        *,
        source_batch_id=None,
        manual=False,
    ):
        request = (
            SharePointSyncRequest(
                source_batch_id=(
                    source_batch_id
                ),
                manual=bool(
                    manual
                ),
            )
        )

        if not self._running:
            self._running = True
            self._current = request
            return request

        if self._pending is None:
            self._pending = request
            return None

        batch_id = (
            request.source_batch_id
            or
            self._pending.source_batch_id
        )

        self._pending = (
            SharePointSyncRequest(
                source_batch_id=batch_id,
                manual=(
                    self._pending.manual
                    or request.manual
                ),
            )
        )

        return None

    def complete(
        self,
    ):
        if not self._running:
            return None

        if self._pending is None:
            self._running = False
            self._current = None
            return None

        next_request = (
            self._pending
        )

        self._pending = None
        self._current = next_request

        return next_request
