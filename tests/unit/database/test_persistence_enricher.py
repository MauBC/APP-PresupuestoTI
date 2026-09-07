from datetime import (
    datetime,
    timezone,
)

import pandas as pd
import pytest

from database.bootstrap.persistence_enricher import (
    FINAL_STORAGE_COLUMNS,
    TECHNICAL_COLUMNS,
    PersistenceEnrichmentError,
    enrich_for_persistence,
)
from database.bootstrap.schema import (
    STORAGE_BUSINESS_COLUMNS,
)


pytestmark = pytest.mark.unit


FIXED_TIME = datetime(
    2026,
    9,
    5,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)


def make_projected_dataframe(
    row_count=2,
):
    rows = []

    for index in range(
        row_count
    ):
        row = {
            column: None
            for column
            in STORAGE_BUSINESS_COLUMNS
        }

        row[
            "pais"
        ] = "PERU"

        row[
            "nombre_gasto"
        ] = (
            f"GASTO {index + 1}"
        )

        row[
            "enero_usd"
        ] = 100 + index

        rows.append(
            row
        )

    return pd.DataFrame(
        rows
    )


def make_id_factory():
    counter = {
        "value": 0
    }

    def factory():
        counter[
            "value"
        ] += 1

        return (
            "row-"
            f"{counter['value']}"
        )

    return factory


def test_final_schema_has_67_columns():
    assert (
        len(
            STORAGE_BUSINESS_COLUMNS
        )
        == 60
    )

    assert (
        len(
            TECHNICAL_COLUMNS
        )
        == 7
    )

    assert (
        len(
            FINAL_STORAGE_COLUMNS
        )
        == 67
    )


def test_enrichment_adds_all_technical_columns():
    dataframe = (
        make_projected_dataframe()
    )

    enriched = (
        enrich_for_persistence(
            dataframe,
            actor="test@ransa.net",
            timestamp=FIXED_TIME,
            row_id_factory=(
                make_id_factory()
            ),
        )
    )

    assert tuple(
        enriched.columns
    ) == FINAL_STORAGE_COLUMNS


def test_row_ids_are_unique():
    dataframe = (
        make_projected_dataframe(
            row_count=3
        )
    )

    enriched = (
        enrich_for_persistence(
            dataframe,
            actor="test@ransa.net",
            timestamp=FIXED_TIME,
            row_id_factory=(
                make_id_factory()
            ),
        )
    )

    assert enriched[
        "row_id"
    ].tolist() == [
        "row-1",
        "row-2",
        "row-3",
    ]

    assert (
        enriched[
            "row_id"
        ].nunique()
        == 3
    )


def test_rows_start_enabled():
    enriched = (
        enrich_for_persistence(
            make_projected_dataframe(),
            actor="test@ransa.net",
            timestamp=FIXED_TIME,
            row_id_factory=(
                make_id_factory()
            ),
        )
    )

    assert enriched[
        "habilitado"
    ].tolist() == [
        True,
        True,
    ]


def test_rows_start_at_version_one():
    enriched = (
        enrich_for_persistence(
            make_projected_dataframe(),
            actor="test@ransa.net",
            timestamp=FIXED_TIME,
            row_id_factory=(
                make_id_factory()
            ),
        )
    )

    assert enriched[
        "version"
    ].tolist() == [
        1,
        1,
    ]


def test_creation_and_update_metadata_match():
    enriched = (
        enrich_for_persistence(
            make_projected_dataframe(),
            actor="test@ransa.net",
            timestamp=FIXED_TIME,
            row_id_factory=(
                make_id_factory()
            ),
        )
    )

    assert all(
        value == FIXED_TIME
        for value
        in enriched[
            "created_at"
        ]
    )

    assert all(
        value == FIXED_TIME
        for value
        in enriched[
            "updated_at"
        ]
    )

    assert all(
        value == "test@ransa.net"
        for value
        in enriched[
            "created_by"
        ]
    )

    assert all(
        value == "test@ransa.net"
        for value
        in enriched[
            "updated_by"
        ]
    )


def test_business_values_are_preserved():
    dataframe = (
        make_projected_dataframe()
    )

    enriched = (
        enrich_for_persistence(
            dataframe,
            actor="test@ransa.net",
            timestamp=FIXED_TIME,
            row_id_factory=(
                make_id_factory()
            ),
        )
    )

    assert (
        enriched.loc[
            0,
            "pais",
        ]
        == "PERU"
    )

    assert (
        enriched.loc[
            0,
            "nombre_gasto",
        ]
        == "GASTO 1"
    )

    assert (
        enriched.loc[
            0,
            "enero_usd",
        ]
        == 100
    )


def test_original_dataframe_is_not_modified():
    dataframe = (
        make_projected_dataframe()
    )

    original = dataframe.copy(
        deep=True
    )

    enrich_for_persistence(
        dataframe,
        actor="test@ransa.net",
        timestamp=FIXED_TIME,
        row_id_factory=(
            make_id_factory()
        ),
    )

    pd.testing.assert_frame_equal(
        dataframe,
        original,
    )


def test_empty_actor_is_rejected():
    with pytest.raises(
        PersistenceEnrichmentError,
        match="usuario",
    ):
        enrich_for_persistence(
            make_projected_dataframe(),
            actor="   ",
            timestamp=FIXED_TIME,
            row_id_factory=(
                make_id_factory()
            ),
        )


def test_naive_timestamp_is_rejected():
    naive = datetime(
        2026,
        9,
        5,
        12,
        0,
        0,
    )

    with pytest.raises(
        PersistenceEnrichmentError,
        match="zona horaria",
    ):
        enrich_for_persistence(
            make_projected_dataframe(),
            actor="test@ransa.net",
            timestamp=naive,
            row_id_factory=(
                make_id_factory()
            ),
        )


def test_duplicate_row_ids_are_rejected():
    def duplicate_factory():
        return "same-id"

    with pytest.raises(
        PersistenceEnrichmentError,
        match="duplicados",
    ):
        enrich_for_persistence(
            make_projected_dataframe(),
            actor="test@ransa.net",
            timestamp=FIXED_TIME,
            row_id_factory=(
                duplicate_factory
            ),
        )


def test_missing_business_column_is_rejected():
    dataframe = (
        make_projected_dataframe()
        .drop(
            columns=[
                "pais"
            ]
        )
    )

    with pytest.raises(
        PersistenceEnrichmentError,
        match="pais",
    ):
        enrich_for_persistence(
            dataframe,
            actor="test@ransa.net",
            timestamp=FIXED_TIME,
            row_id_factory=(
                make_id_factory()
            ),
        )