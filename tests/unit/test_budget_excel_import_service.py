
from itertools import count

import pandas as pd
import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.config.capex_schema import (
    CAPEX_BUSINESS_TYPES,
    CAPEX_INTERNAL_TO_RAW,
    CAPEX_RAW_TO_INTERNAL,
)
from app.config.presupuesto_schema import (
    AMOUNT_COLUMNS,
    LEGACY_EXPECTED_COLUMNS,
    STRING_COLUMNS,
)
from app.services.budget_excel_import_service import (
    BudgetExcelImportService,
)


pytestmark = pytest.mark.unit


def id_factory(
    prefix,
):
    sequence = count(
        1
    )

    return lambda: (
        f"{prefix}-"
        f"{next(sequence)}"
    )


def make_opex_dataframe(
    *,
    bad_amount=False,
):
    row = {}

    for column in (
        LEGACY_EXPECTED_COLUMNS
    ):
        if column in STRING_COLUMNS:
            row[column] = None

        else:
            row[column] = 0

    row["pais"] = "PER"
    row["presupuestador"] = (
        "M8E TEST"
    )
    row["nombre_gasto"] = (
        "IMPORT TEST"
    )
    row["moneda_facturacion"] = (
        "USD"
    )

    if bad_amount:
        row["enero_usd"] = (
            "NO-ES-NUMERO"
        )

    return pd.DataFrame(
        [row],
        columns=(
            LEGACY_EXPECTED_COLUMNS
        ),
    )


def make_capex_dataframe():
    row = {}

    for raw, internal in (
        CAPEX_RAW_TO_INTERNAL.items()
    ):
        value_type = (
            CAPEX_BUSINESS_TYPES[
                internal
            ]
        )

        if value_type == "STRING":
            value = "TEST"

        elif value_type == "INTEGER":
            value = 1

        else:
            value = 0

        row[raw] = value

    row[
        CAPEX_INTERNAL_TO_RAW[
            "tipo"
        ]
    ] = "CAPEX"

    row[
        CAPEX_INTERNAL_TO_RAW[
            "pais"
        ]
    ] = "PER"

    row[
        CAPEX_INTERNAL_TO_RAW[
            "anio"
        ]
    ] = 2027

    row[
        CAPEX_INTERNAL_TO_RAW[
            "cantidad"
        ]
    ] = 1

    row[
        CAPEX_INTERNAL_TO_RAW[
            "nombre_inversion"
        ]
    ] = "M8E TEST"

    row[
        CAPEX_INTERNAL_TO_RAW[
            "moneda_facturacion"
        ]
    ] = "USD"

    return pd.DataFrame(
        [row],
        columns=tuple(
            CAPEX_RAW_TO_INTERNAL
        ),
    )


def test_real_opex_excel_preparation(
    tmp_path,
):
    path = (
        tmp_path
        / "opex.xlsx"
    )

    make_opex_dataframe().to_excel(
        path,
        index=False,
    )

    result = (
        BudgetExcelImportService(
            OPEX_MODULE_CONFIG
        )
        .prepare(
            path,
            actor="tester",
            row_id_factory=(
                id_factory(
                    "opex"
                )
            ),
        )
    )

    assert result.is_valid
    assert result.rows_read == 1
    assert result.importable_count == 1

    row = result.rows[0]

    assert row["pais"] == "PER"
    assert row["version"] == 1

    assert set(
        OPEX_MODULE_CONFIG
        .insert_columns
    ).issubset(
        row
    )


def test_invalid_opex_amount_blocks_entire_import(
    tmp_path,
):
    path = (
        tmp_path
        / "opex_bad.xlsx"
    )

    make_opex_dataframe(
        bad_amount=True
    ).to_excel(
        path,
        index=False,
    )

    result = (
        BudgetExcelImportService(
            OPEX_MODULE_CONFIG
        )
        .prepare(
            path,
            actor="tester",
        )
    )

    assert not result.is_valid
    assert result.error_count == 1

    assert (
        result.importable_count
        == 0
    )


def test_real_capex_excel_preparation(
    tmp_path,
):
    path = (
        tmp_path
        / "capex.xlsx"
    )

    with pd.ExcelWriter(
        path,
        engine="openpyxl",
    ) as writer:
        make_capex_dataframe().to_excel(
            writer,
            sheet_name="PB 2027",
            index=False,
        )

    result = (
        BudgetExcelImportService(
            CAPEX_MODULE_CONFIG
        )
        .prepare(
            path,
            actor="tester",
            expected_year=2027,
            row_id_factory=(
                id_factory(
                    "capex"
                )
            ),
        )
    )

    assert result.is_valid
    assert result.rows_read == 1
    assert result.importable_count == 1

    row = result.rows[0]

    assert row["tipo"] == "CAPEX"
    assert row["pais"] == "PER"
    assert row["anio"] == 2027
    assert row["cantidad"] == 1
    assert row["version"] == 1

    assert set(
        CAPEX_MODULE_CONFIG
        .insert_columns
    ).issubset(
        row
    )


def test_capex_same_project_different_ceco_is_allowed(
    tmp_path,
):
    path = (
        tmp_path
        / "capex_multi_ceco.xlsx"
    )

    dataframe = (
        make_capex_dataframe()
    )

    second = dataframe.copy(
        deep=True
    )

    second.loc[
        0,
        CAPEX_INTERNAL_TO_RAW[
            "codigo_ceco"
        ],
    ] = "CECO-002"

    dataframe.loc[
        0,
        CAPEX_INTERNAL_TO_RAW[
            "codigo_ceco"
        ],
    ] = "CECO-001"

    combined = pd.concat(
        (
            dataframe,
            second,
        ),
        ignore_index=True,
    )

    with pd.ExcelWriter(
        path,
        engine="openpyxl",
    ) as writer:
        combined.to_excel(
            writer,
            sheet_name="PB 2027",
            index=False,
        )

    result = (
        BudgetExcelImportService(
            CAPEX_MODULE_CONFIG
        )
        .prepare(
            path,
            actor="tester",
            expected_year=2027,
            row_id_factory=(
                id_factory(
                    "multi"
                )
            ),
        )
    )

    assert result.is_valid

    assert (
        result.rows_read
        == 2
    )

    assert (
        result.importable_count
        == 2
    )

    assert (
        result.rows[0][
            "nombre_inversion"
        ]
        ==
        result.rows[1][
            "nombre_inversion"
        ]
    )

    assert {
        result.rows[0][
            "codigo_ceco"
        ],
        result.rows[1][
            "codigo_ceco"
        ],
    } == {
        "CECO-001",
        "CECO-002",
    }

    assert (
        result.rows[0][
            "row_id"
        ]
        !=
        result.rows[1][
            "row_id"
        ]
    )

def test_opex_import_ignores_ghost_rows(
    tmp_path,
):
    path = (
        tmp_path
        / "opex_ghost_rows.xlsx"
    )

    ghost = {
        column: "-"
        for column
        in LEGACY_EXPECTED_COLUMNS
    }

    dataframe = pd.concat(
        (
            pd.DataFrame(
                [ghost],
                columns=(
                    LEGACY_EXPECTED_COLUMNS
                ),
            ),
            make_opex_dataframe(),
        ),
        ignore_index=True,
    )

    dataframe.to_excel(
        path,
        index=False,
    )

    result = (
        BudgetExcelImportService(
            OPEX_MODULE_CONFIG
        )
        .prepare(
            path,
            actor="tester",
            row_id_factory=(
                id_factory(
                    "ghost"
                )
            ),
        )
    )

    assert result.is_valid

    assert (
        result.rows_read
        == 1
    )

    assert (
        result.importable_count
        == 1
    )

    assert (
        result.ignored_row_count
        == 1
    )

    assert (
        result.source_row_numbers
        == (
            3,
        )
    )


def test_opex_zero_is_not_a_ghost_row(
    tmp_path,
):
    path = (
        tmp_path
        / "opex_zero.xlsx"
    )

    dataframe = (
        make_opex_dataframe()
    )

    dataframe.loc[
        0,
        "enero_usd",
    ] = 0

    dataframe.to_excel(
        path,
        index=False,
    )

    result = (
        BudgetExcelImportService(
            OPEX_MODULE_CONFIG
        )
        .prepare(
            path,
            actor="tester",
            row_id_factory=(
                id_factory(
                    "zero"
                )
            ),
        )
    )

    assert (
        result.rows_read
        == 1
    )

    assert (
        result.ignored_row_count
        == 0
    )

    assert (
        result.source_row_numbers
        == (
            2,
        )
    )
