from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from app.config.capex_schema import (
    CAPEX_AMOUNT_COLUMNS,
    CAPEX_BUSINESS_COLUMNS,
    CAPEX_EXPECTED_COLUMNS,
    CAPEX_INTEGER_COLUMNS,
)
from database.bootstrap import (
    capex_full_load_bigquery,
)
from database.bootstrap.capex_bigquery_contract import (
    build_capex_bigquery_schema,
)
from database.bootstrap.capex_full_load_bigquery import (
    CapexFullLoadBigQueryError,
    run_capex_full_load,
)
from database.bootstrap.capex_full_load_validation import (
    CapexFullLoadMetrics,
    CapexFullLoadValidationError,
)


pytestmark = pytest.mark.unit


class FakeLoadJob:
    def result(
        self,
    ):
        return None


class FakeClient:
    def __init__(
        self,
    ):
        self.load_calls = 0

    def get_table(
        self,
        table_id,
    ):
        return SimpleNamespace(
            schema=list(
                build_capex_bigquery_schema()
            )
        )

    def load_table_from_dataframe(
        self,
        dataframe,
        table_id,
        *,
        job_config,
        location,
    ):
        self.load_calls += 1
        return FakeLoadJob()


def make_dataframe(
    rows=2,
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
                    "10.000000000"
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
                ] = "value"

        record[
            "row_id"
        ] = (
            f"row-{index}"
        )

        record[
            "habilitado"
        ] = True

        record[
            "version"
        ] = 1

        record[
            "created_at"
        ] = "timestamp"

        record[
            "created_by"
        ] = "tester"

        record[
            "updated_at"
        ] = "timestamp"

        record[
            "updated_by"
        ] = "tester"

        records.append(
            record
        )

    return pd.DataFrame(
        records,
        columns=(
            CAPEX_EXPECTED_COLUMNS
        ),
    )


def test_full_load_success_keeps_rows(
    monkeypatch,
):
    client = FakeClient()

    monkeypatch.setattr(
        capex_full_load_bigquery,
        "get_capex_table_row_count",
        lambda *args, **kwargs: 0,
    )

    monkeypatch.setattr(
        capex_full_load_bigquery,
        "read_capex_full_load_metrics",
        lambda *args, **kwargs:
            CapexFullLoadMetrics(
                total_rows=2,
                unique_row_ids=2,
                disabled_rows=0,
                min_version=1,
                max_version=1,
                years=(
                    2027,
                ),
            ),
    )

    deleted = []

    monkeypatch.setattr(
        capex_full_load_bigquery,
        "delete_capex_rows",
        lambda *args, **kwargs:
            deleted.append(
                kwargs
            ),
    )

    result = (
        run_capex_full_load(
            client,
            make_dataframe(),
            table_id=(
                "project.dataset.capex_2027"
            ),
            location="US",
            expected_rows=2,
            expected_year=2027,
        )
    )

    assert result.total_rows == 2
    assert result.unique_row_ids == 2
    assert result.years == (2027,)
    assert client.load_calls == 1

    assert deleted == []


def test_full_load_rejects_nonempty_table(
    monkeypatch,
):
    client = FakeClient()

    monkeypatch.setattr(
        capex_full_load_bigquery,
        "get_capex_table_row_count",
        lambda *args, **kwargs: 3,
    )

    with pytest.raises(
        CapexFullLoadBigQueryError,
        match="debe estar vacia",
    ):
        run_capex_full_load(
            client,
            make_dataframe(),
            table_id=(
                "project.dataset.capex_2027"
            ),
            location="US",
            expected_rows=2,
            expected_year=2027,
        )

    assert client.load_calls == 0


def test_validation_failure_triggers_cleanup(
    monkeypatch,
):
    client = FakeClient()

    counts = iter(
        (
            0,
            0,
        )
    )

    monkeypatch.setattr(
        capex_full_load_bigquery,
        "get_capex_table_row_count",
        lambda *args, **kwargs:
            next(
                counts
            ),
    )

    monkeypatch.setattr(
        capex_full_load_bigquery,
        "read_capex_full_load_metrics",
        lambda *args, **kwargs:
            CapexFullLoadMetrics(
                total_rows=1,
                unique_row_ids=1,
                disabled_rows=0,
                min_version=1,
                max_version=1,
                years=(
                    2027,
                ),
            ),
    )

    deleted = []

    monkeypatch.setattr(
        capex_full_load_bigquery,
        "delete_capex_rows",
        lambda *args, **kwargs:
            deleted.append(
                tuple(
                    kwargs[
                        "row_ids"
                    ]
                )
            ),
    )

    with pytest.raises(
        CapexFullLoadBigQueryError,
        match="fueron eliminadas",
    ):
        run_capex_full_load(
            client,
            make_dataframe(),
            table_id=(
                "project.dataset.capex_2027"
            ),
            location="US",
            expected_rows=2,
            expected_year=2027,
        )

    assert client.load_calls == 1

    assert deleted == [
        (
            "row-0",
            "row-1",
        )
    ]
