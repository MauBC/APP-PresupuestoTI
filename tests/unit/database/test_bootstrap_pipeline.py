from datetime import (
    datetime,
    timezone,
)

import pandas as pd
import pytest

from app.config.presupuesto_schema import (
    LEGACY_EXPECTED_COLUMNS,
)
from database.bootstrap.pipeline import (
    BootstrapPreparationError,
    prepare_budget,
)


pytestmark = pytest.mark.unit


FIXED_TIME = datetime(
    2026,
    9,
    5,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_source_dataframe(
    row_count=1,
):
    rows = []

    for index in range(
        row_count
    ):
        row = {
            column: ""
            for column
            in LEGACY_EXPECTED_COLUMNS
        }

        row.update(
            {
                "pais": "PERU",
                "vp": "VP",
                "vp2": "VP2",
                "nombre_gasto": (
                    f"GASTO {index + 1}"
                ),
                "enero_usd": (
                    str(
                        100 + index
                    )
                ),
                "anio_usd": (
                    str(
                        100 + index
                    )
                ),
            }
        )

        rows.append(
            row
        )

    return pd.DataFrame(
        rows
    )


def write_source(
    tmp_path,
    dataframe,
):
    path = (
        tmp_path
        / "presupuesto.csv"
    )

    dataframe.to_csv(
        path,
        index=False,
        encoding="utf-8",
    )

    return path


def make_id_factory():
    counter = {
        "value": 0
    }

    def factory():
        counter[
            "value"
        ] += 1

        return (
            f"id-{counter['value']}"
        )

    return factory


def test_prepare_budget_end_to_end(
    tmp_path,
):
    path = write_source(
        tmp_path,
        make_source_dataframe(),
    )

    result = prepare_budget(
        path,
        actor="test@ransa.net",
        timestamp=FIXED_TIME,
        row_id_factory=(
            make_id_factory()
        ),
    )

    assert result.final_row_count == 1
    assert result.final_column_count == 67
    assert result.unique_row_id_count == 1


def test_prepare_removes_vp_columns(
    tmp_path,
):
    path = write_source(
        tmp_path,
        make_source_dataframe(),
    )

    result = prepare_budget(
        path,
        actor="test@ransa.net",
        timestamp=FIXED_TIME,
        row_id_factory=(
            make_id_factory()
        ),
    )

    assert "vp" not in (
        result.dataframe.columns
    )

    assert "vp2" not in (
        result.dataframe.columns
    )

    assert (
        result.projection
        .dropped_columns
        == (
            "vp",
            "vp2",
        )
    )


def test_prepare_preserves_business_values(
    tmp_path,
):
    path = write_source(
        tmp_path,
        make_source_dataframe(),
    )

    result = prepare_budget(
        path,
        actor="test@ransa.net",
        timestamp=FIXED_TIME,
        row_id_factory=(
            make_id_factory()
        ),
    )

    assert (
        result.dataframe.loc[
            0,
            "pais",
        ]
        == "PERU"
    )

    assert (
        result.dataframe.loc[
            0,
            "nombre_gasto",
        ]
        == "GASTO 1"
    )


def test_prepare_adds_metadata(
    tmp_path,
):
    path = write_source(
        tmp_path,
        make_source_dataframe(),
    )

    result = prepare_budget(
        path,
        actor="test@ransa.net",
        timestamp=FIXED_TIME,
        row_id_factory=(
            make_id_factory()
        ),
    )

    row = (
        result.dataframe.iloc[0]
    )

    assert row[
        "row_id"
    ] == "id-1"

    assert bool(
        row["habilitado"]
    )

    assert row[
        "version"
    ] == 1

    assert row[
        "created_by"
    ] == "test@ransa.net"

    assert row[
        "updated_by"
    ] == "test@ransa.net"


def test_extra_column_is_reported_and_ignored(
    tmp_path,
):
    dataframe = (
        make_source_dataframe()
    )

    dataframe[
        "vp1"
    ] = "VP1"

    path = write_source(
        tmp_path,
        dataframe,
    )

    result = prepare_budget(
        path,
        actor="test@ransa.net",
        timestamp=FIXED_TIME,
        row_id_factory=(
            make_id_factory()
        ),
    )

    assert (
        "vp1"
        in result.cleaning
        .extra_columns
    )

    assert "vp1" not in (
        result.dataframe.columns
    )


def test_invalid_amount_rejects_prepare(
    tmp_path,
):
    dataframe = (
        make_source_dataframe()
    )

    dataframe.loc[
        0,
        "enero_usd",
    ] = "INVALIDO"

    path = write_source(
        tmp_path,
        dataframe,
    )

    with pytest.raises(
        BootstrapPreparationError,
        match="errores",
    ) as error:
        prepare_budget(
            path,
            actor="test@ransa.net",
            timestamp=FIXED_TIME,
            row_id_factory=(
                make_id_factory()
            ),
        )

    cleaning = (
        error.value
        .cleaning_result
    )

    assert cleaning is not None
    assert len(
        cleaning.issues
    ) == 1

    assert (
        cleaning.issues[0]
        .column
        == "enero_usd"
    )


def test_prepare_preserves_row_count(
    tmp_path,
):
    path = write_source(
        tmp_path,
        make_source_dataframe(
            row_count=3
        ),
    )

    result = prepare_budget(
        path,
        actor="test@ransa.net",
        timestamp=FIXED_TIME,
        row_id_factory=(
            make_id_factory()
        ),
    )

    assert (
        result.source_row_count
        == 3
    )

    assert (
        result.final_row_count
        == 3
    )


def test_prepare_generates_unique_ids(
    tmp_path,
):
    path = write_source(
        tmp_path,
        make_source_dataframe(
            row_count=3
        ),
    )

    result = prepare_budget(
        path,
        actor="test@ransa.net",
        timestamp=FIXED_TIME,
        row_id_factory=(
            make_id_factory()
        ),
    )

    assert (
        result.unique_row_id_count
        == 3
    )