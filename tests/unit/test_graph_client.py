import pytest

from app.clients.graph_client import (
    GraphClient,
    GraphClientError,
)


pytestmark = pytest.mark.unit


class FakeAuth:
    def get_access_token(
        self,
    ):
        return "fake-token"


class FakeResponse:
    def __init__(
        self,
        *,
        status_code=200,
        payload=None,
        headers=None,
    ):
        self.status_code = status_code
        self._payload = (
            payload
            if payload is not None
            else {}
        )
        self.headers = {
            "Content-Type":
                "application/json",
            **(
                headers
                or {}
            ),
        }

        self.content = b"{}"
        self.text = "{}"

    @property
    def ok(
        self,
    ):
        return (
            200
            <= self.status_code
            < 300
        )

    def json(
        self,
    ):
        return self._payload


class FakeSession:
    def __init__(
        self,
        responses,
    ):
        self._responses = list(
            responses
        )

        self.calls = []

    def request(
        self,
        **kwargs,
    ):
        self.calls.append(
            kwargs
        )

        if not self._responses:
            raise AssertionError(
                "No quedan respuestas fake."
            )

        return self._responses.pop(
            0
        )


def build_client(
    payload,
):
    session = FakeSession(
        (
            FakeResponse(
                payload=payload
            ),
        )
    )

    client = GraphClient(
        auth_service=FakeAuth(),
        session=session,
        sleep_func=lambda seconds: None,
    )

    return client


def test_empty_graph_page_is_valid():
    client = build_client(
        {
            "value": []
        }
    )

    result = (
        client.get_all_pages(
            "/sites/site/lists/list/items"
        )
    )

    assert result == ()


def test_graph_page_returns_items():
    client = build_client(
        {
            "value": [
                {
                    "id": "1"
                },
                {
                    "id": "2"
                },
            ]
        }
    )

    result = (
        client.get_all_pages(
            "/sites/site/lists/list/items"
        )
    )

    assert result == (
        {
            "id": "1"
        },
        {
            "id": "2"
        },
    )


def test_invalid_value_type_is_rejected():
    client = build_client(
        {
            "value": {
                "id": "1"
            }
        }
    )

    with pytest.raises(
        GraphClientError,
        match="dict",
    ):
        client.get_all_pages(
            "/sites/site/lists/list/items"
        )
