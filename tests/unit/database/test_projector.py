import pandas as pd
import pytest

from app.config.presupuesto_schema import (
    LEGACY_EXPECTED_COLUMNS,
)
from database.bootstrap.projector import (
    ProjectionError,
    project_dataframe,
)
from database.bootstrap.schema import (
    IGNORED_SOURCE_COLUMNS,
    STORAGE_AMOUNT_COLUMNS,
    STORAGE_BUSINESS_COLUMNS,
    STORAGE_STRING_COLUMNS,
)


pytestmark = pytest.mark.unit


def make_source_dataframe():
    row = {
        column: None
        for column
        in LEGACY_EXPECTED_COLUMNS
    }

    row.update(
        {
            "pais": "PERU",
            "vp": "VP TEST",
            "vp2": "VP2 TEST",
            "enero_usd": 100,
            "anio_usd": 100,
        }
    )

    return pd.DataFrame(
        [row]
    )


def test_storage_schema_has_60_business_columns():
    assert (
        len(STORAGE_STRING_COLUMNS)
        == 21
    )

    assert (
        len(STORAGE_AMOUNT_COLUMNS)
        == 39
    )

    assert (
        len(STORAGE_BUSINESS_COLUMNS)
        == 60
    )


def test_deprecated_columns_are_not_stored():
    assert "vp" not in (
        STORAGE_BUSINESS_COLUMNS
    )

    assert "vp1" not in (
        STORAGE_BUSINESS_COLUMNS
    )

    assert "vp2" not in (
        STORAGE_BUSINESS_COLUMNS
    )


def test_projector_removes_vp_columns():
    result = project_dataframe(
        make_source_dataframe()
    )

    assert "vp" not in (
        result.dataframe.columns
    )

    assert "vp2" not in (
        result.dataframe.columns
    )

    assert (
        result.dropped_columns
        == (
            "vp",
            "vp2",
        )
    )


def test_projector_keeps_business_values():
    result = project_dataframe(
        make_source_dataframe()
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
            "enero_usd",
        ]
        == 100
    )


def test_projected_column_order_is_stable():
    result = project_dataframe(
        make_source_dataframe()
    )

    assert tuple(
        result.dataframe.columns
    ) == STORAGE_BUSINESS_COLUMNS


def test_projector_does_not_modify_source():
    dataframe = (
        make_source_dataframe()
    )

    original = dataframe.copy(
        deep=True
    )

    project_dataframe(
        dataframe
    )

    pd.testing.assert_frame_equal(
        dataframe,
        original,
    )


def test_missing_business_column_is_rejected():
    dataframe = (
        make_source_dataframe()
        .drop(
            columns=["pais"]
        )
    )

    with pytest.raises(
        ProjectionError,
        match="pais",
    ):
        project_dataframe(
            dataframe
        )


def test_vp1_is_ignored_when_present():
    dataframe = (
        make_source_dataframe()
    )

    dataframe[
        "vp1"
    ] = "VP1 TEST"

    result = project_dataframe(
        dataframe
    )

    assert "vp1" not in (
        result.dataframe.columns
    )

    assert "vp1" in (
        result.dropped_columns
    )


def test_all_ignored_columns_are_configured():
    assert (
        IGNORED_SOURCE_COLUMNS
        == (
            "vp",
            "vp1",
            "vp2",
        )
    )