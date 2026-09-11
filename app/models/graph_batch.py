
from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class GraphBatchRequest:
    request_id: str
    method: str
    url: str

    headers: tuple[
        tuple[str, str],
        ...
    ] = ()

    body: Any = None

    def __post_init__(
        self,
    ):
        request_id = str(
            self.request_id
        ).strip()

        method = str(
            self.method
        ).strip().upper()

        url = str(
            self.url
        ).strip()

        if not request_id:
            raise ValueError(
                "request_id no puede "
                "estar vacio."
            )

        if method not in {
            "GET",
            "POST",
            "PATCH",
            "DELETE",
        }:
            raise ValueError(
                "Metodo Graph batch "
                f"no soportado: {method}"
            )

        if (
            not url
            or not url.startswith("/")
        ):
            raise ValueError(
                "url debe ser relativa "
                "y comenzar con '/'."
            )

        if self.body is not None:
            header_names = {
                str(name)
                .strip()
                .lower()
                for name, _
                in self.headers
            }

            if (
                "content-type"
                not in header_names
            ):
                raise ValueError(
                    "Una operacion batch "
                    "con body requiere "
                    "Content-Type."
                )

        object.__setattr__(
            self,
            "request_id",
            request_id,
        )

        object.__setattr__(
            self,
            "method",
            method,
        )

        object.__setattr__(
            self,
            "url",
            url,
        )

    def as_payload(
        self,
    ) -> dict:
        payload = {
            "id":
                self.request_id,
            "method":
                self.method,
            "url":
                self.url,
        }

        if self.headers:
            payload["headers"] = dict(
                self.headers
            )

        if self.body is not None:
            payload["body"] = (
                self.body
            )

        return payload


@dataclass(
    frozen=True,
    slots=True,
)
class GraphBatchResponse:
    request_id: str
    status: int

    headers: tuple[
        tuple[str, Any],
        ...
    ] = ()

    body: Any = None

    @property
    def is_success(
        self,
    ) -> bool:
        return (
            200
            <= self.status
            < 300
        )


@dataclass(
    frozen=True,
    slots=True,
)
class GraphBatchExecutionResult:
    responses: tuple[
        GraphBatchResponse,
        ...
    ]

    @property
    def success_count(
        self,
    ) -> int:
        return sum(
            1
            for response
            in self.responses
            if response.is_success
        )

    @property
    def failures(
        self,
    ) -> tuple[
        GraphBatchResponse,
        ...
    ]:
        return tuple(
            response
            for response
            in self.responses
            if not response.is_success
        )

    @property
    def failure_count(
        self,
    ) -> int:
        return len(
            self.failures
        )

    @property
    def is_success(
        self,
    ) -> bool:
        return (
            self.failure_count
            == 0
        )
