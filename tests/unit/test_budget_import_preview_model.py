
from decimal import Decimal

import pytest

from PySide6.QtCore import (
    Qt,
)

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.ui.models.budget_import_preview_model import (
    BudgetImportPreviewModel,
    format_import_value,
    import_preview_columns,
)


pytestmark = pytest.mark.unit


def test_preview_uses_full_insert_contract():
    assert (
        import_preview_columns(
            OPEX_MODULE_CONFIG
        )
        ==
        OPEX_MODULE_CONFIG
        .insert_columns
    )

    assert (
        import_preview_columns(
            CAPEX_MODULE_CONFIG
        )
        ==
        CAPEX_MODULE_CONFIG
        .insert_columns
    )


def test_preview_does_not_include_technical_columns():
    columns = (
        import_preview_columns(
            OPEX_MODULE_CONFIG
        )
    )

    assert (
        "row_id"
        not in columns
    )

    assert (
        "version"
        not in columns
    )

    assert (
        "created_by"
        not in columns
    )


def test_decimal_format():
    assert (
        format_import_value(
            Decimal(
                "1234.50"
            )
        )
        == "1,234.50"
    )


def test_none_format():
    assert (
        format_import_value(
            None
        )
        == ""
    )

def test_preview_tracks_source_excel_row():
    model = BudgetImportPreviewModel(
        rows=(
            {
                "pais": "PER",
            },
            {
                "pais": "CHL",
            },
        ),
        module_config=(
            CAPEX_MODULE_CONFIG
        ),
        source_row_numbers=(
            9,
            15,
        ),
    )

    assert (
        model.headerData(
            1,
            Qt.Orientation.Horizontal,
        )
        == "FILA EXCEL"
    )

    assert (
        model.data(
            model.index(
                0,
                1,
            ),
            Qt.ItemDataRole.UserRole,
        )
        == 9
    )

    assert (
        model.data(
            model.index(
                1,
                1,
            ),
            Qt.ItemDataRole.UserRole,
        )
        == 15
    )


def test_preview_rows_start_included():
    model = BudgetImportPreviewModel(
        rows=(
            {"pais": "PER"},
            {"pais": "CHL"},
        ),
        module_config=(
            CAPEX_MODULE_CONFIG
        ),
    )

    assert (
        model.included_count
        == 2
    )

    assert (
        model.excluded_count
        == 0
    )

    assert (
        len(
            model.included_rows()
        )
        == 2
    )


def test_preview_can_exclude_row():
    model = BudgetImportPreviewModel(
        rows=(
            {"pais": "PER"},
            {"pais": "CHL"},
        ),
        module_config=(
            CAPEX_MODULE_CONFIG
        ),
        source_row_numbers=(
            8,
            9,
        ),
    )

    changed = (
        model.set_included(
            1,
            False,
        )
    )

    assert changed

    assert (
        model.included_count
        == 1
    )

    assert (
        model.excluded_count
        == 1
    )

    rows = (
        model.included_rows()
    )

    assert (
        len(rows)
        == 1
    )

    assert (
        rows[0]["pais"]
        == "PER"
    )


def test_preview_include_all_restores_rows():
    model = BudgetImportPreviewModel(
        rows=(
            {"pais": "PER"},
            {"pais": "CHL"},
        ),
        module_config=(
            OPEX_MODULE_CONFIG
        ),
    )

    model.set_included(
        0,
        False,
    )

    assert (
        model.included_count
        == 1
    )

    model.include_all()

    assert (
        model.included_count
        == 2
    )

    assert (
        model.excluded_count
        == 0
    )


def test_preview_checkbox_updates_inclusion():
    model = BudgetImportPreviewModel(
        rows=(
            {"pais": "PER"},
        ),
        module_config=(
            CAPEX_MODULE_CONFIG
        ),
    )

    index = model.index(
        0,
        0,
    )

    assert (
        model.data(
            index,
            Qt.ItemDataRole.CheckStateRole,
        )
        == Qt.CheckState.Checked
    )

    assert model.setData(
        index,
        Qt.CheckState.Unchecked,
        Qt.ItemDataRole.CheckStateRole,
    )

    assert (
        model.included_count
        == 0
    )

    assert (
        model.data(
            index,
            Qt.ItemDataRole.CheckStateRole,
        )
        == Qt.CheckState.Unchecked
    )


def test_preview_rejects_mismatched_source_rows():
    with pytest.raises(
        ValueError,
        match="source_row_numbers",
    ):
        BudgetImportPreviewModel(
            rows=(
                {"pais": "PER"},
                {"pais": "CHL"},
            ),
            module_config=(
                CAPEX_MODULE_CONFIG
            ),
            source_row_numbers=(
                9,
            ),
        )
