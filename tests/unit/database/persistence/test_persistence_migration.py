import pytest

from google.api_core.exceptions import (
    NotFound,
)
from google.cloud import bigquery

from database.migrations.persistence_tables import (
    PersistenceMigrationError,
    ensure_persistence_tables,
)


pytestmark = pytest.mark.unit


PROJECT = "project-test"
DATASET = "dataset_test"
LOCATION = "US"


class FakeDataset:
    def __init__(
        self,
        location="US",
    ):
        self.location = location


class FakeBigQueryClient:
    def __init__(
        self,
        *,
        location="US",
    ):
        self.dataset = (
            FakeDataset(
                location=location
            )
        )

        self.tables = {}
        self.create_calls = []

    def get_dataset(
        self,
        dataset_id,
    ):
        return self.dataset

    def get_table(
        self,
        table_id,
    ):
        table = (
            self.tables.get(
                table_id
            )
        )

        if table is None:
            raise NotFound(
                "Table not found."
            )

        return table

    def create_table(
        self,
        table,
        exists_ok=False,
    ):
        table_id = (
            f"{table.project}."
            f"{table.dataset_id}."
            f"{table.table_id}"
        )

        self.create_calls.append(
            table_id
        )

        if (
            table_id in self.tables
            and not exists_ok
        ):
            raise RuntimeError(
                "Table already exists."
            )

        if table_id not in self.tables:
            self.tables[
                table_id
            ] = table

        return self.tables[
            table_id
        ]


def test_dry_run_does_not_create_tables():
    client = (
        FakeBigQueryClient()
    )

    result = (
        ensure_persistence_tables(
            client,
            project=PROJECT,
            dataset=DATASET,
            location=LOCATION,
            apply=False,
        )
    )

    assert (
        result.pending_count
        == 3
    )

    assert (
        result.created_count
        == 0
    )

    assert (
        client.create_calls
        == []
    )

    assert {
        item.status
        for item in result.tables
    } == {
        "WOULD_CREATE"
    }


def test_apply_creates_three_tables():
    client = (
        FakeBigQueryClient()
    )

    result = (
        ensure_persistence_tables(
            client,
            project=PROJECT,
            dataset=DATASET,
            location=LOCATION,
            apply=True,
        )
    )

    assert (
        result.created_count
        == 3
    )

    assert len(
        client.create_calls
    ) == 3

    assert len(
        client.tables
    ) == 3


def test_second_execution_is_idempotent():
    client = (
        FakeBigQueryClient()
    )

    ensure_persistence_tables(
        client,
        project=PROJECT,
        dataset=DATASET,
        location=LOCATION,
        apply=True,
    )

    first_create_count = len(
        client.create_calls
    )

    result = (
        ensure_persistence_tables(
            client,
            project=PROJECT,
            dataset=DATASET,
            location=LOCATION,
            apply=True,
        )
    )

    assert (
        result.existing_count
        == 3
    )

    assert (
        result.created_count
        == 0
    )

    assert len(
        client.create_calls
    ) == first_create_count


def test_incompatible_existing_schema_is_rejected():
    client = (
        FakeBigQueryClient()
    )

    table_id = (
        f"{PROJECT}."
        f"{DATASET}."
        "presupuesto_change_batches"
    )

    client.tables[
        table_id
    ] = bigquery.Table(
        table_id,
        schema=[
            bigquery.SchemaField(
                "batch_id",
                "STRING",
                mode="REQUIRED",
            ),
        ],
    )

    with pytest.raises(
        PersistenceMigrationError,
        match="no coincide",
    ):
        ensure_persistence_tables(
            client,
            project=PROJECT,
            dataset=DATASET,
            location=LOCATION,
            apply=False,
        )


def test_location_mismatch_is_rejected():
    client = (
        FakeBigQueryClient(
            location="EU"
        )
    )

    with pytest.raises(
        PersistenceMigrationError,
        match="ubicacion",
    ):
        ensure_persistence_tables(
            client,
            project=PROJECT,
            dataset=DATASET,
            location="US",
            apply=False,
        )
