
import time

from app.models.graph_batch import (
    GraphBatchExecutionResult,
    GraphBatchResponse,
)


class GraphBatchClientError(
    RuntimeError
):
    pass


class GraphBatchClient:
    MAX_BATCH_SIZE = 20

    RETRY_STATUS = {
        429,
        500,
        502,
        503,
        504,
    }

    def __init__(
        self,
        graph_client,
        *,
        max_retries: int = 5,
        sleep_func=time.sleep,
    ):
        if (
            isinstance(
                max_retries,
                bool,
            )
            or not isinstance(
                max_retries,
                int,
            )
            or max_retries < 1
        ):
            raise ValueError(
                "max_retries debe ser "
                "entero mayor a cero."
            )

        self._graph = graph_client
        self._max_retries = (
            max_retries
        )
        self._sleep = sleep_func

    def execute(
        self,
        requests,
    ) -> GraphBatchExecutionResult:
        requests = tuple(
            requests
        )

        if not requests:
            return (
                GraphBatchExecutionResult(
                    responses=(),
                )
            )

        request_ids = [
            request.request_id
            for request
            in requests
        ]

        if (
            len(request_ids)
            != len(set(request_ids))
        ):
            raise GraphBatchClientError(
                "Existen request_id "
                "duplicados en Graph batch."
            )

        results = []

        for start in range(
            0,
            len(requests),
            self.MAX_BATCH_SIZE,
        ):
            chunk = requests[
                start:
                start
                + self.MAX_BATCH_SIZE
            ]

            chunk_result = (
                self._execute_chunk(
                    chunk
                )
            )

            results.extend(
                chunk_result.responses
            )

            if not chunk_result.is_success:
                break

        return (
            GraphBatchExecutionResult(
                responses=tuple(
                    results
                ),
            )
        )

    def _execute_chunk(
        self,
        requests,
    ) -> GraphBatchExecutionResult:
        pending = {
            request.request_id:
                request
            for request
            in requests
        }

        final = {}

        for attempt in range(
            self._max_retries
        ):
            if not pending:
                break

            payload = {
                "requests": [
                    request.as_payload()
                    for request
                    in pending.values()
                ]
            }

            data = (
                self._graph
                .post(
                    "/$batch",
                    json_body=payload,
                )
            )

            if not isinstance(
                data,
                dict,
            ):
                raise GraphBatchClientError(
                    "Respuesta Graph batch "
                    "invalida."
                )

            raw_responses = (
                data.get(
                    "responses"
                )
            )

            if not isinstance(
                raw_responses,
                list,
            ):
                raise GraphBatchClientError(
                    "Graph batch no devolvio "
                    "responses validas."
                )

            by_id = {}

            for raw in raw_responses:
                if not isinstance(
                    raw,
                    dict,
                ):
                    raise (
                        GraphBatchClientError(
                            "Respuesta individual "
                            "Graph batch invalida."
                        )
                    )

                response_id = str(
                    raw.get(
                        "id",
                        "",
                    )
                ).strip()

                if not response_id:
                    raise (
                        GraphBatchClientError(
                            "Respuesta Graph batch "
                            "sin id."
                        )
                    )

                if response_id in by_id:
                    raise (
                        GraphBatchClientError(
                            "Graph batch devolvio "
                            "un id duplicado."
                        )
                    )

                if response_id not in pending:
                    raise (
                        GraphBatchClientError(
                            "Graph batch devolvio "
                            "un id no solicitado."
                        )
                    )

                by_id[
                    response_id
                ] = raw

            missing = (
                set(pending)
                - set(by_id)
            )

            if missing:
                raise GraphBatchClientError(
                    "Graph batch omitio "
                    "respuestas: "
                    + ", ".join(
                        sorted(
                            missing
                        )
                    )
                )

            retry = {}
            retry_delays = []
            non_retryable_failure = False

            for (
                request_id,
                request,
            ) in pending.items():
                raw = by_id[
                    request_id
                ]

                try:
                    status = int(
                        raw.get(
                            "status"
                        )
                    )

                except (
                    TypeError,
                    ValueError,
                ) as exc:
                    raise (
                        GraphBatchClientError(
                            "Graph batch devolvio "
                            "status invalido."
                        )
                    ) from exc

                headers = (
                    raw.get(
                        "headers"
                    )
                    or {}
                )

                if not isinstance(
                    headers,
                    dict,
                ):
                    headers = {}

                response = (
                    GraphBatchResponse(
                        request_id=(
                            request_id
                        ),
                        status=status,
                        headers=tuple(
                            headers.items()
                        ),
                        body=raw.get(
                            "body"
                        ),
                    )
                )

                if response.is_success:
                    final[
                        request_id
                    ] = response

                    continue

                can_retry = (
                    status
                    in self.RETRY_STATUS
                    and
                    attempt
                    < self._max_retries - 1
                )

                if can_retry:
                    retry[
                        request_id
                    ] = request

                    retry_delays.append(
                        self._retry_delay(
                            headers,
                            attempt,
                        )
                    )

                else:
                    final[
                        request_id
                    ] = response

                    non_retryable_failure = True

            if non_retryable_failure:
                for request_id in retry:
                    raw = by_id[
                        request_id
                    ]

                    final[
                        request_id
                    ] = GraphBatchResponse(
                        request_id=(
                            request_id
                        ),
                        status=int(
                            raw["status"]
                        ),
                        headers=tuple(
                            (
                                raw.get(
                                    "headers"
                                )
                                or {}
                            ).items()
                        ),
                        body=raw.get(
                            "body"
                        ),
                    )

                break

            pending = retry

            if pending:
                self._sleep(
                    max(
                        retry_delays
                        or [
                            float(
                                min(
                                    2 ** attempt,
                                    30,
                                )
                            )
                        ]
                    )
                )

        ordered = []

        for request in requests:
            response = final.get(
                request.request_id
            )

            if response is None:
                raise GraphBatchClientError(
                    "Graph batch termino "
                    "sin resultado final para "
                    f"{request.request_id}."
                )

            ordered.append(
                response
            )

        return (
            GraphBatchExecutionResult(
                responses=tuple(
                    ordered
                ),
            )
        )

    @staticmethod
    def _retry_delay(
        headers,
        attempt,
    ) -> float:
        normalized = {
            str(key).lower():
                value
            for key, value
            in headers.items()
        }

        retry_after = (
            normalized.get(
                "retry-after"
            )
        )

        if retry_after is not None:
            try:
                return min(
                    float(
                        retry_after
                    ),
                    60.0,
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        retry_ms = (
            normalized.get(
                "x-ms-retry-after-ms"
            )
        )

        if retry_ms is not None:
            try:
                return min(
                    float(
                        retry_ms
                    )
                    / 1000.0,
                    60.0,
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        return float(
            min(
                2 ** attempt,
                30,
            )
        )
