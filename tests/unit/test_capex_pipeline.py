from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config.capex_schema import (
    CAPEX_AMOUNT_COLUMNS,
    CAPEX_BUSINESS_COLUMNS,
    CAPEX_EXPECTED_COLUMNS,
    CAPEX_INTEGER_COLUMNS,
)
from database.bootstrap import (
    capex_pipeline,
)
from database.bootstrap.capex_pipeline import (
    CapexBootstrapPreparationError,
    prepare_capex_bootstrap,
)


pytestmark = pytest.mark.unit


def make_clean_row(
    index=0,
):
    row = {}

    for column in (
        CAPEX_BUSINESS_COLUMNS
    ):
        if (
            column
            in CAPEX_AMOUNT_COLUMNS
        ):
            row[
                column
            ] = Decimal(
                "10.000000000"
            )

        elif (
            column
            in CAPEX_INTEGER_COLUMNS
        ):
            row[
                column
            ] = (
                2027
                if column
                == "anio"
                else 1
            )

        else:
            row[
                column
            ] = (
                f"value-{index}"
            )

    row[
        "codigo_cebe"
    ] = (
        "04WF2EAF90"
    )

    row[
        "codigo_ceco"
    ] = (
        "04WF2EAF93"
    )

    return row


def make_import_result(
    *,
    rows=2,
    invalid_count=0,
):
    results = tuple(
        SimpleNamespace(
            row=make_clean_row(
                index
            ),
            is_valid=True,
        )
        for index
        in range(
            rows
        )
    )

    return SimpleNamespace(
        source_path=(
            "capex.xlsx"
        ),
        rows_read=rows,
        invalid_count=(
            invalid_count
        ),
        valid_results=results,
    )


def test_prepare_capex_builds_final_contract(
    monkeypatch,
    tmp_path,
):
    source = (
        tmp_path
        / "capex.xlsx"
    )

    source.write_bytes(
        b"fake"
    )

    import_result = (
        make_import_result(
            rows=2
        )
    )

    monkeypatch.setattr(
        capex_pipeline,
        "load_capex_workbook",
        lambda *args, **kwargs:
            import_result,
    )

    row_ids = iter(
        (
            "row-1",
            "row-2",
        )
    )

    timestamp = datetime(
        2027,
        1,
        1,
        tzinfo=timezone.utc,
    )

    result = (
        prepare_capex_bootstrap(
            source,
            actor="tester",
            expected_year=2027,
            timestamp=timestamp,
            row_id_factory=(
                lambda: next(
                    row_ids
                )
            ),
        )
    )

    assert (
        result.source_path
        == source.resolve()
    )

    assert (
        result.source_row_count
        == 2
    )

    assert (
        result.business_column_count
        == 51
    )

    assert (
        result.final_row_count
        == 2
    )

    assert (
        result.final_column_count
        == 58
    )

    assert (
        result.unique_row_id_count
        == 2
    )

    assert tuple(
        result.dataframe.columns
    ) == tuple(
        CAPEX_EXPECTED_COLUMNS
    )

    assert list(
        result.dataframe[
            "row_id"
        ]
    ) == [
        "row-1",
        "row-2",
    ]

    assert (
        result.dataframe[
            "version"
        ]
        .tolist()
        == [
            1,
            1,
        ]
    )


def test_prepare_capex_preserves_codes(
    monkeypatch,
    tmp_path,
):
    source = (
        tmp_path
        / "capex.xlsx"
    )

    source.write_bytes(
        b"fake"
    )

    monkeypatch.setattr(
        capex_pipeline,
        "load_capex_workbook",
        lambda *args, **kwargs:
            make_import_result(
                rows=1
            ),
    )

    result = (
        prepare_capex_bootstrap(
            source,
            actor="tester",
            row_id_factory=(
                lambda: "row-1"
            ),
        )
    )

    assert (
        result.dataframe.loc[
            0,
            "codigo_cebe",
        ]
        == "04WF2EAF90"
    )

    assert (
        result.dataframe.loc[
            0,
            "codigo_ceco",
        ]
        == "04WF2EAF93"
    )


def test_prepare_capex_rejects_invalid_rows(
    monkeypatch,
    tmp_path,
):
    source = (
        tmp_path
        / "capex.xlsx"
    )

    source.write_bytes(
        b"fake"
    )

    monkeypatch.setattr(
        capex_pipeline,
        "load_capex_workbook",
        lambda *args, **kwargs:
            make_import_result(
                rows=2,
                invalid_count=1,
            ),
    )

    with pytest.raises(
        CapexBootstrapPreparationError,
        match="filas con errores",
    ):
        prepare_capex_bootstrap(
            source,
            actor="tester",
        )


def test_prepare_capex_rejects_empty_actor(
    tmp_path,
):
    source = (
        tmp_path
        / "capex.xlsx"
    )

    source.write_bytes(
        b"fake"
    )

    with pytest.raises(
        CapexBootstrapPreparationError,
        match="actor",
    ):
        prepare_capex_bootstrap(
            source,
            actor=" ",
        )


def test_prepare_capex_rejects_empty_import(
    monkeypatch,
    tmp_path,
):
    source = (
        tmp_path
        / "capex.xlsx"
    )

    source.write_bytes(
        b"fake"
    )

    monkeypatch.setattr(
        capex_pipeline,
        "load_capex_workbook",
        lambda *args, **kwargs:
            make_import_result(
                rows=0
            ),
    )

    with pytest.raises(
        CapexBootstrapPreparationError,
        match="no contiene filas",
    ):
        prepare_capex_bootstrap(
            source,
            actor="tester",
        )
