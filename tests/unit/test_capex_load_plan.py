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
    CAPEX_INTEGER_COLUMNS,
)
from database.bootstrap.capex_load_plan import (
    CapexLoadPlanError,
    build_capex_load_plan,
)
from database.bootstrap.capex_persistence_enricher import (
    enrich_capex_for_persistence,
)


pytestmark = pytest.mark.unit


def make_final_dataframe(
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

        records.append(
            record
        )

    source = pd.DataFrame(
        records,
        columns=(
            CAPEX_BUSINESS_COLUMNS
        ),
    )

    row_ids = iter(
        f"row-{index}"
        for index in range(
            rows
        )
    )

    return enrich_capex_for_persistence(
        source,
        actor="tester",
        timestamp=datetime(
            2027,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        row_id_factory=lambda: next(
            row_ids
        ),
    )


def test_build_capex_load_plan():
    dataframe = (
        make_final_dataframe(
            rows=2
        )
    )

    plan = (
        build_capex_load_plan(
            dataframe,
            project="proyecto",
            dataset="presupuesto_ti",
            table="capex_2027",
            location="US",
        )
    )

    assert (
        plan.table_id
        == (
            "proyecto."
            "presupuesto_ti."
            "capex_2027"
        )
    )

    assert plan.row_count == 2
    assert plan.column_count == 58

    assert (
        plan.write_disposition
        == "WRITE_TRUNCATE"
    )


def test_capex_load_plan_rejects_empty_dataframe():
    dataframe = (
        make_final_dataframe()
        .iloc[0:0]
        .copy()
    )

    with pytest.raises(
        CapexLoadPlanError,
        match="vacio",
    ):
        build_capex_load_plan(
            dataframe,
            project="proyecto",
            dataset="presupuesto_ti",
            table="capex_2027",
        )


def test_capex_load_plan_rejects_duplicate_row_ids():
    dataframe = (
        make_final_dataframe(
            rows=2
        )
    )

    dataframe.loc[
        1,
        "row_id",
    ] = dataframe.loc[
        0,
        "row_id",
    ]

    with pytest.raises(
        CapexLoadPlanError,
        match="duplicados",
    ):
        build_capex_load_plan(
            dataframe,
            project="proyecto",
            dataset="presupuesto_ti",
            table="capex_2027",
        )


def test_capex_load_plan_rejects_wrong_columns():
    dataframe = (
        make_final_dataframe()
        .drop(
            columns=[
                "codigo_cebe"
            ]
        )
    )

    with pytest.raises(
        CapexLoadPlanError,
        match="esquema final",
    ):
        build_capex_load_plan(
            dataframe,
            project="proyecto",
            dataset="presupuesto_ti",
            table="capex_2027",
        )
