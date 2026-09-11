
from decimal import Decimal

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.ui.models.budget_import_preview_model import (
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
