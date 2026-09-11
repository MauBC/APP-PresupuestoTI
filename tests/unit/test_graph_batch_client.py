
import pytest

from app.clients.graph_batch_client import (
    GraphBatchClient,
)
from app.models.graph_batch import (
    GraphBatchRequest,
)


pytestmark = pytest.mark.unit


def request(
    request_id,
):
    return (
        GraphBatchRequest(
            request_id=str(
                request_id
            ),
            method="POST",
            url="/sites/site/lists/list/items",
            headers=(
                (
                    "Content-Type",
                    "application/json",
                ),
            ),
            body={
                "fields": {
                    "Title":
                        str(
                            request_id
                        )
                }
            },
        )
    )


class SuccessGraph:
    def __init__(self):
        self.calls = []

    def post(
        self,
        endpoint,
        *,
        json_body,
    ):
        self.calls.append(
            (
                endpoint,
                json_body,
            )
        )

        return {
            "responses": [
                {
                    "id":
                        item["id"],
                    "status":
                        201,
                    "headers":
                        {},
                    "body": {
                        "id":
                            item["id"]
                    },
                }
                for item
                in json_body[
                    "requests"
                ]
            ]
        }


def test_batch_splits_at_twenty():
    graph = SuccessGraph()

    result = (
        GraphBatchClient(
            graph
        )
        .execute(
            tuple(
                request(index)
                for index
                in range(21)
            )
        )
    )

    assert result.is_success
    assert result.success_count == 21
    assert len(graph.calls) == 2

    assert (
        len(
            graph.calls[0][1][
                "requests"
            ]
        )
        == 20
    )

    assert (
        len(
            graph.calls[1][1][
                "requests"
            ]
        )
        == 1
    )


class RetryGraph:
    def __init__(self):
        self.calls = 0

    def post(
        self,
        endpoint,
        *,
        json_body,
    ):
        self.calls += 1

        if self.calls == 1:
            return {
                "responses": [
                    {
                        "id":
                            json_body[
                                "requests"
                            ][0]["id"],
                        "status":
                            429,
                        "headers": {
                            "Retry-After":
                                "0"
                        },
                        "body": {
                            "error":
                                "throttled"
                        },
                    }
                ]
            }

        return {
            "responses": [
                {
                    "id":
                        json_body[
                            "requests"
                        ][0]["id"],
                    "status":
                        201,
                    "headers":
                        {},
                    "body": {
                        "id": "1"
                    },
                }
            ]
        }


def test_batch_retries_internal_429():
    graph = RetryGraph()

    result = (
        GraphBatchClient(
            graph,
            sleep_func=(
                lambda seconds:
                    None
            ),
        )
        .execute(
            (
                request("1"),
            )
        )
    )

    assert result.is_success
    assert graph.calls == 2


class ForbiddenGraph:
    def post(
        self,
        endpoint,
        *,
        json_body,
    ):
        return {
            "responses": [
                {
                    "id":
                        json_body[
                            "requests"
                        ][0]["id"],
                    "status":
                        403,
                    "headers":
                        {},
                    "body": {
                        "error": {
                            "code":
                                "accessDenied"
                        }
                    },
                }
            ]
        }


def test_non_retryable_failure_is_returned():
    result = (
        GraphBatchClient(
            ForbiddenGraph()
        )
        .execute(
            (
                request("1"),
            )
        )
    )

    assert not result.is_success
    assert result.failure_count == 1
    assert (
        result.failures[0].status
        == 403
    )


def test_batch_request_with_body_requires_content_type():
    with pytest.raises(
        ValueError,
        match="Content-Type",
    ):
        GraphBatchRequest(
            request_id="1",
            method="POST",
            url="/items",
            body={
                "test": True
            },
        )
