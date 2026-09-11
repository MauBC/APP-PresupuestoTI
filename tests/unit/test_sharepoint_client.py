
import pytest

from app.clients.sharepoint_client import (
    SharePointClient,
    SharePointClientError,
)


pytestmark = pytest.mark.unit


class FakeGraph:
    def __init__(self):
        self.get_calls = []
        self.page_calls = []
        self.post_calls = []
        self.patch_calls = []
        self.delete_calls = []

    def get(
        self,
        endpoint,
        **kwargs,
    ):
        self.get_calls.append(
            endpoint
        )

        return {
            "id": "site-001",
            "displayName":
                "Presupuesto",
        }

    def get_all_pages(
        self,
        endpoint,
        **kwargs,
    ):
        self.page_calls.append(
            (
                endpoint,
                kwargs,
            )
        )

        if endpoint.endswith(
            "/lists"
        ):
            return (
                {
                    "id": "list-001",
                    "name":
                        "Resumen_Capex",
                    "displayName":
                        "Resumen_Capex",
                },
            )

        if endpoint.endswith(
            "/columns"
        ):
            return (
                {
                    "name": "Title",
                    "displayName":
                        "Title",
                },
            )

        if endpoint.endswith(
            "/items"
        ):
            return ()

        raise AssertionError(
            endpoint
        )

    def post(
        self,
        endpoint,
        **kwargs,
    ):
        self.post_calls.append(
            (
                endpoint,
                kwargs,
            )
        )

        return {
            "id": "1"
        }

    def patch(
        self,
        endpoint,
        **kwargs,
    ):
        self.patch_calls.append(
            (
                endpoint,
                kwargs,
            )
        )

        return {
            "Title": "Updated"
        }

    def delete(
        self,
        endpoint,
        **kwargs,
    ):
        self.delete_calls.append(
            (
                endpoint,
                kwargs,
            )
        )

        return None


def build_client():
    return SharePointClient(
        graph_client=FakeGraph(),
        hostname=(
            "gruporansa.sharepoint.com"
        ),
        site_path=(
            "/sites/Presupuesto"
        ),
    )


def test_resolves_site_and_list():
    client = build_client()

    assert (
        client.get_site_id()
        == "site-001"
    )

    assert (
        client.get_list_id(
            "Resumen_Capex"
        )
        == "list-001"
    )


def test_site_and_list_are_cached():
    client = build_client()

    client.get_site_id()
    client.get_site_id()

    client.get_list_id(
        "Resumen_Capex"
    )

    client.get_list_id(
        "Resumen_Capex"
    )

    assert (
        len(
            client._graph
            .get_calls
        )
        == 1
    )

    list_calls = [
        call
        for call in (
            client._graph
            .page_calls
        )
        if call[0].endswith(
            "/lists"
        )
    ]

    assert len(
        list_calls
    ) == 1


def test_reads_items_with_fields():
    client = build_client()

    assert (
        client.get_items(
            "Resumen_Capex"
        )
        == ()
    )

    endpoint, kwargs = (
        client._graph
        .page_calls[-1]
    )

    assert endpoint.endswith(
        "/items"
    )

    assert (
        kwargs["params"]
        ==
        {
            "$expand":
                "fields"
        }
    )


def test_create_item_uses_fields_wrapper():
    client = build_client()

    result = (
        client.create_item(
            "Resumen_Capex",
            {
                "Title":
                    "Proyecto A"
            },
        )
    )

    assert (
        result["id"]
        == "1"
    )

    _, kwargs = (
        client._graph
        .post_calls[-1]
    )

    assert kwargs == {
        "json_body": {
            "fields": {
                "Title":
                    "Proyecto A"
            }
        }
    }


def test_update_item_uses_fields_endpoint():
    client = build_client()

    client.update_item_fields(
        "Resumen_Capex",
        "15",
        {
            "TotalUSD": 100
        },
    )

    endpoint, _ = (
        client._graph
        .patch_calls[-1]
    )

    assert endpoint.endswith(
        "/items/15/fields"
    )


def test_delete_item():
    client = build_client()

    client.delete_item(
        "Resumen_Capex",
        "15",
    )

    endpoint, _ = (
        client._graph
        .delete_calls[-1]
    )

    assert endpoint.endswith(
        "/items/15"
    )


def test_unknown_list_fails():
    client = build_client()

    with pytest.raises(
        SharePointClientError,
        match="No se encontro",
    ):
        client.get_list_id(
            "NoExiste"
        )
