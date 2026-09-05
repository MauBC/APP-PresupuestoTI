from datetime import (
    datetime,
    timezone,
)

import pandas as pd
import pytest

from database.bootstrap.load_plan import (
    LoadPlanError,
    build_load_plan,
)
from database.bootstrap.persistence_enricher import (
    FINAL_STORAGE_COLUMNS,
)
from database.bootstrap.schema import (
    STORAGE_BUSINESS_COLUMNS,
)


pytestmark = pytest.mark.unit


FIXED_TIME = datetime(
    2026,
    9,
    5,
    tzinfo=timezone.utc,
)


def make_prepared_dataframe(
    row_count=2,
):
    rows = []

    for index in range(
        row_count
    ):
        row = {
            column: None
            for column
            in FINAL_STORAGE_COLUMNS
        }

        for column in (
            STORAGE_BUSINESS_COLUMNS
        ):
            row[
                column
            ] = None

        row.update(
            {
                "pais": "PERU",
                "row_id": (
                    f"id-{index + 1}"
                ),
                "habilitado": True,
                "version": 1,
                "created_at": FIXED_TIME,
                "created_by": (
                    "test@ransa.net"
                ),
                "updated_at": FIXED_TIME,
                "updated_by": (
                    "test@ransa.net"
                ),
            }
        )

        rows.append(
            row
        )

    return pd.DataFrame(
        rows,
        columns=(
            FINAL_STORAGE_COLUMNS
        ),
    )


def test_build_load_plan():
    dataframe = (
        make_prepared_dataframe()
    )

    plan = build_load_plan(
        dataframe,
        project="proyecto-test",
        dataset="presupuesto",
        table="presupuesto_2026",
    )

    assert (
        plan.table_id
        == (
            "proyecto-test."
            "presupuesto."
            "presupuesto_2026"
        )
    )

    assert plan.row_count == 2
    assert plan.column_count == 67


def test_plan_uses_write_truncate():
    plan = build_load_plan(
        make_prepared_dataframe(),
        project="project",
        dataset="dataset",
        table="table",
    )

    assert (
        plan.write_disposition
        == "WRITE_TRUNCATE"
    )


def test_empty_dataframe_is_rejected():
    dataframe = pd.DataFrame(
        columns=(
            FINAL_STORAGE_COLUMNS
        )
    )

    with pytest.raises(
        LoadPlanError,
        match="vacio",
    ):
        build_load_plan(
            dataframe,
            project="project",
            dataset="dataset",
            table="table",
        )


def test_wrong_schema_is_rejected():
    dataframe = (
        make_prepared_dataframe()
        .drop(
            columns=["pais"]
        )
    )

    with pytest.raises(
        LoadPlanError,
        match="esquema",
    ):
        build_load_plan(
            dataframe,
            project="project",
            dataset="dataset",
            table="table",
        )


def test_duplicate_row_ids_are_rejected():
    dataframe = (
        make_prepared_dataframe()
    )

    dataframe.loc[
        1,
        "row_id",
    ] = "id-1"

    with pytest.raises(
        LoadPlanError,
        match="duplicados",
    ):
        build_load_plan(
            dataframe,
            project="project",
            dataset="dataset",
            table="table",
        )


def test_null_version_is_rejected():
    dataframe = (
        make_prepared_dataframe()
    )

    dataframe.loc[
        0,
        "version",
    ] = None

    with pytest.raises(
        LoadPlanError,
        match="version",
    ):
        build_load_plan(
            dataframe,
            project="project",
            dataset="dataset",
            table="table",
        )


def test_empty_project_is_rejected():
    with pytest.raises(
        LoadPlanError,
        match="project",
    ):
        build_load_plan(
            make_prepared_dataframe(),
            project="",
            dataset="dataset",
            table="table",
        )