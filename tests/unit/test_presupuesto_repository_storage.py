from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)
from app.repositories.presupuesto_repository import (
    PresupuestoRepository,
)


pytestmark = pytest.mark.unit


class FakeArrowTable:
    def __init__(
        self,
        rows,
    ):
        self._rows = rows

    def to_pylist(
        self,
    ):
        return [
            dict(row)
            for row
            in self._rows
        ]


class StorageIterator:
    def __init__(
        self,
        rows,
    ):
        self.rows = rows
        self.storage_requested = False
        self.iterated = False

    def to_arrow(
        self,
        *,
        create_bqstorage_client,
    ):
        self.storage_requested = (
            create_bqstorage_client
        )

        return FakeArrowTable(
            self.rows
        )

    def __iter__(
        self,
    ):
        self.iterated = True

        raise AssertionError(
            "No debe usar REST "
            "cuando Storage funciona."
        )


class BrokenStorageIterator:
    def to_arrow(
        self,
        *,
        create_bqstorage_client,
    ):
        raise RuntimeError(
            "Storage no disponible"
        )


class RestIterator:
    def __init__(
        self,
        rows,
    ):
        self.rows = rows

    def __iter__(
        self,
    ):
        return iter(
            self.rows
        )


class FakeClient:
    def __init__(
        self,
        iterators,
    ):
        self.iterators = list(
            iterators
        )

        self.calls = 0

        self.selected_names = []

    def list_rows(
        self,
        table,
        *,
        selected_fields,
    ):
        self.calls += 1

        self.selected_names.append(
            tuple(
                field.name
                for field
                in selected_fields
            )
        )

        return self.iterators.pop(
            0
        )


class FakeBigQuery:
    def __init__(
        self,
        client,
    ):
        self.client = client

        self.table = SimpleNamespace(
            schema=(
                SimpleNamespace(
                    name="pais"
                ),
                SimpleNamespace(
                    name="enero_usd"
                ),
                SimpleNamespace(
                    name="row_id"
                ),
                SimpleNamespace(
                    name="version"
                ),
                SimpleNamespace(
                    name="habilitado"
                ),
            )
        )

    def get_table(
        self,
        table_name,
    ):
        return self.table


def test_get_all_rows_prefers_storage_arrow():
    amount = Decimal(
        "123.456789123"
    )

    iterator = StorageIterator(
        (
            {
                "pais": "PE",
                "enero_usd": amount,
                "row_id": "row-1",
                "version": 3,
                "habilitado": True,
            },
        )
    )

    client = FakeClient(
        (
            iterator,
        )
    )

    repository = (
        PresupuestoRepository(
            FakeBigQuery(
                client
            ),
            module_config=(
                OPEX_MODULE_CONFIG
            ),
        )
    )

    rows = repository.get_all_rows()

    assert len(rows) == 1

    assert (
        rows[0]["enero_usd"]
        == amount
    )

    assert isinstance(
        rows[0]["enero_usd"],
        Decimal,
    )

    assert (
        iterator.storage_requested
        is True
    )

    assert (
        iterator.iterated
        is False
    )

    assert client.calls == 1


def test_get_all_rows_falls_back_to_rest():
    amount = Decimal(
        "50.25"
    )

    client = FakeClient(
        (
            BrokenStorageIterator(),
            RestIterator(
                (
                    {
                        "pais": "CO",
                        "enero_usd":
                            amount,
                        "row_id":
                            "row-2",
                        "version":
                            4,
                        "habilitado":
                            False,
                    },
                )
            ),
        )
    )

    repository = (
        PresupuestoRepository(
            FakeBigQuery(
                client
            ),
            module_config=(
                OPEX_MODULE_CONFIG
            ),
        )
    )

    rows = repository.get_all_rows()

    assert len(rows) == 1

    assert (
        rows[0]["row_id"]
        == "row-2"
    )

    assert (
        rows[0]["habilitado"]
        is False
    )

    assert (
        rows[0]["enero_usd"]
        == amount
    )

    assert client.calls == 2


def test_storage_preserves_schema_order():
    iterator = StorageIterator(
        ()
    )

    client = FakeClient(
        (
            iterator,
        )
    )

    repository = (
        PresupuestoRepository(
            FakeBigQuery(
                client
            ),
            module_config=(
                OPEX_MODULE_CONFIG
            ),
        )
    )

    repository.get_all_rows()

    assert client.selected_names == [
        (
            "pais",
            "enero_usd",
            "row_id",
            "version",
            "habilitado",
        )
    ]


def test_capex_uses_rest_without_storage():
    from app.config.budget_modules import (
        CAPEX_MODULE_CONFIG,
    )

    rows = (
        {
            "pais": "PE",
            "row_id": "capex-1",
            "version": 2,
            "habilitado": True,
        },
    )

    client = FakeClient(
        (
            RestIterator(
                rows
            ),
        )
    )

    repository = (
        PresupuestoRepository(
            FakeBigQuery(
                client
            ),
            module_config=(
                CAPEX_MODULE_CONFIG
            ),
        )
    )

    result = repository.get_all_rows()

    assert len(result) == 1
    assert result[0]["row_id"] == "capex-1"

    # CAPEX debe resolver todo
    # con una sola llamada REST.
    assert client.calls == 1
