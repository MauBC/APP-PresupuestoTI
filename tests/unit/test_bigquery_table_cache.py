from types import SimpleNamespace

import pytest

from app.services.bigquery_service import (
    BigQueryService,
)


pytestmark = pytest.mark.unit


class FakeClient:
    def __init__(
        self,
        *,
        table,
    ):
        self.table = table
        self.calls = 0

    def get_table(
        self,
        table_ref,
    ):
        self.calls += 1

        return self.table


def configure_reference(
    service,
):
    service.get_table_reference = (
        lambda table_name=None:
            "project.dataset."
            + (
                table_name
                or "default_table"
            )
    )


def test_default_services_share_table_metadata():
    BigQueryService.clear_table_cache()

    table = SimpleNamespace(
        schema=("field",)
    )

    first_client = FakeClient(
        table=table
    )

    second_client = FakeClient(
        table=table
    )

    first = BigQueryService()
    first._client = first_client
    configure_reference(
        first
    )

    second = BigQueryService()
    second._client = second_client
    configure_reference(
        second
    )

    first_result = (
        first.get_cached_table(
            "presupuesto_2026"
        )
    )

    second_result = (
        second.get_cached_table(
            "presupuesto_2026"
        )
    )

    assert first_result is table
    assert second_result is table

    assert first_client.calls == 1
    assert second_client.calls == 0

    BigQueryService.clear_table_cache()


def test_injected_client_does_not_share_cache():
    BigQueryService.clear_table_cache()

    table = SimpleNamespace(
        schema=("field",)
    )

    client = FakeClient(
        table=table
    )

    service = BigQueryService(
        client=client
    )

    configure_reference(
        service
    )

    service.get_cached_table(
        "presupuesto_2026"
    )

    service.get_cached_table(
        "presupuesto_2026"
    )

    assert client.calls == 2

    BigQueryService.clear_table_cache()


def test_clear_table_cache_forces_reload():
    BigQueryService.clear_table_cache()

    table = SimpleNamespace(
        schema=("field",)
    )

    client = FakeClient(
        table=table
    )

    service = BigQueryService()
    service._client = client

    configure_reference(
        service
    )

    service.get_cached_table(
        "presupuesto_2026"
    )

    BigQueryService.clear_table_cache()

    service.get_cached_table(
        "presupuesto_2026"
    )

    assert client.calls == 2

    BigQueryService.clear_table_cache()
