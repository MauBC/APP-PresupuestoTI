from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pandas as pd
import pytest

from app.config.capex_schema import (
    CAPEX_AMOUNT_COLUMNS,
    CAPEX_BUSINESS_COLUMNS,
    CAPEX_EXPECTED_COLUMNS,
    CAPEX_INTEGER_COLUMNS,
)
from database.bootstrap.capex_persistence_enricher import (
    CapexPersistenceEnrichmentError,
    enrich_capex_for_persistence,
)


pytestmark = pytest.mark.unit


def make_business_dataframe(
    rows=1,
):
    records = []

    for index in range(
        rows
    ):
        record = {}

        for column in (
            CAPEX_BUSINESS_COLUMNS
        ):
            if (
                column
                in CAPEX_AMOUNT_COLUMNS
            ):
                record[
                    column
                ] = Decimal(
                    "0.000000000"
                )

            elif (
                column
                in CAPEX_INTEGER_COLUMNS
            ):
                record[
                    column
                ] = (
                    2027
                    if column
                    == "anio"
                    else 1
                )

            else:
                record[
                    column
                ] = (
                    f"value-{index}"
                )

        records.append(
            record
        )

    return pd.DataFrame(
        records,
        columns=(
            CAPEX_BUSINESS_COLUMNS
        ),
    )


def test_enricher_builds_58_columns():
    dataframe = (
        make_business_dataframe()
    )

    timestamp = datetime(
        2027,
        1,
        1,
        tzinfo=timezone.utc,
    )

    enriched = (
        enrich_capex_for_persistence(
            dataframe,
            actor="tester",
            timestamp=timestamp,
            row_id_factory=(
                lambda: "row-1"
            ),
        )
    )

    assert tuple(
        enriched.columns
    ) == tuple(
        CAPEX_EXPECTED_COLUMNS
    )

    assert (
        len(
            enriched.columns
        )
        == 58
    )

    assert (
        enriched.loc[
            0,
            "row_id",
        ]
        == "row-1"
    )

    assert bool(
        enriched.loc[
            0,
            "habilitado",
        ]
    )

    assert (
        enriched.loc[
            0,
            "version",
        ]
        == 1
    )

    assert (
        enriched.loc[
            0,
            "created_at",
        ]
        == timestamp
    )

    assert (
        enriched.loc[
            0,
            "updated_at",
        ]
        == timestamp
    )

    assert (
        enriched.loc[
            0,
            "created_by",
        ]
        == "tester"
    )

    assert (
        enriched.loc[
            0,
            "updated_by",
        ]
        == "tester"
    )


def test_enricher_rejects_empty_actor():
    dataframe = (
        make_business_dataframe()
    )

    with pytest.raises(
        CapexPersistenceEnrichmentError,
        match="usuario",
    ):
        enrich_capex_for_persistence(
            dataframe,
            actor=" ",
        )


def test_enricher_rejects_naive_timestamp():
    dataframe = (
        make_business_dataframe()
    )

    with pytest.raises(
        CapexPersistenceEnrichmentError,
        match="zona horaria",
    ):
        enrich_capex_for_persistence(
            dataframe,
            actor="tester",
            timestamp=datetime(
                2027,
                1,
                1,
            ),
        )


def test_enricher_rejects_duplicate_row_ids():
    dataframe = (
        make_business_dataframe(
            rows=2
        )
    )

    with pytest.raises(
        CapexPersistenceEnrichmentError,
        match="duplicados",
    ):
        enrich_capex_for_persistence(
            dataframe,
            actor="tester",
            row_id_factory=(
                lambda: "same-id"
            ),
        )


def test_enricher_rejects_extra_columns():
    dataframe = (
        make_business_dataframe()
    )

    dataframe[
        "extra"
    ] = "x"

    with pytest.raises(
        CapexPersistenceEnrichmentError,
        match="no esperadas",
    ):
        enrich_capex_for_persistence(
            dataframe,
            actor="tester",
        )
