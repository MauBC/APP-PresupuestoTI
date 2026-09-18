from decimal import Decimal

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.services.budget_row_edit_service import (
    BudgetRowEditError,
    BudgetRowEditService,
)

pytestmark = pytest.mark.unit


def make_row(config):
    row = {}
    for column, value_type in config.insert_column_types:
        if value_type == "STRING":
            row[column] = "X"
        elif value_type == "INTEGER":
            row[column] = 2027 if column == "anio" else 1
        elif value_type == "NUMERIC":
            row[column] = Decimal("0")
        else:
            raise AssertionError(value_type)
    return row


def test_opex_string_preserves_leading_zeroes():
    row = make_row(OPEX_MODULE_CONFIG)
    result = BudgetRowEditService(OPEX_MODULE_CONFIG).edit_value(
        row, "ceco", " 001234 "
    )
    assert result["ceco"] == "001234"


def test_opex_mf_month_recalculates_annual():
    row = make_row(OPEX_MODULE_CONFIG)
    result = BudgetRowEditService(OPEX_MODULE_CONFIG).edit_value(
        row, "enero_mf", "10.25"
    )
    assert result["enero_mf"] == Decimal("10.25")
    assert result["anio_mf"] == Decimal("10.25")


def test_opex_ml_annual_redistributes_same_family():
    row = make_row(OPEX_MODULE_CONFIG)
    row["enero_ml"] = Decimal("1")
    row["febrero_ml"] = Decimal("3")
    row["anio_ml"] = Decimal("4")
    result = BudgetRowEditService(OPEX_MODULE_CONFIG).edit_value(
        row, "anio_ml", "8"
    )
    assert result["enero_ml"] == Decimal("2.00")
    assert result["febrero_ml"] == Decimal("6.00")
    assert result["anio_ml"] == Decimal("8.00")


def test_capex_integer_is_strict():
    row = make_row(CAPEX_MODULE_CONFIG)
    result = BudgetRowEditService(CAPEX_MODULE_CONFIG).edit_value(
        row, "cantidad", "3"
    )
    assert result["cantidad"] == 3
    with pytest.raises(BudgetRowEditError, match="entero"):
        BudgetRowEditService(CAPEX_MODULE_CONFIG).edit_value(
            row, "cantidad", "3.5"
        )


def test_capex_code_preserves_value():
    row = make_row(CAPEX_MODULE_CONFIG)
    result = BudgetRowEditService(CAPEX_MODULE_CONFIG).edit_value(
        row, "codigo_ceco", "04WF2EAF93"
    )
    assert result["codigo_ceco"] == "04WF2EAF93"


def test_capex_ml_keeps_nine_decimal_precision():
    row = make_row(CAPEX_MODULE_CONFIG)
    result = BudgetRowEditService(CAPEX_MODULE_CONFIG).edit_value(
        row, "enero_ml", "1.123456789"
    )
    assert result["enero_ml"] == Decimal("1.123456789")
    assert result["anio_ml"] == Decimal("1.123456789")


def test_capex_annual_distribution_conserves_total():
    row = make_row(CAPEX_MODULE_CONFIG)
    row["enero_usd"] = Decimal("1")
    row["febrero_usd"] = Decimal("1")
    row["marzo_usd"] = Decimal("1")
    row["anio_usd"] = Decimal("3")
    result = BudgetRowEditService(CAPEX_MODULE_CONFIG).edit_value(
        row, "anio_usd", "10"
    )
    total = sum(
        (result[column] for column in CAPEX_MODULE_CONFIG.month_columns),
        Decimal("0"),
    )
    assert total == Decimal("10.000000000")
    assert result["anio_usd"] == Decimal("10.000000000")


def test_negative_amount_rejected():
    row = make_row(CAPEX_MODULE_CONFIG)
    with pytest.raises(BudgetRowEditError, match="negativo"):
        BudgetRowEditService(CAPEX_MODULE_CONFIG).edit_value(
            row, "enero_usd", "-1"
        )


def test_technical_column_rejected():
    row = make_row(OPEX_MODULE_CONFIG)
    with pytest.raises(BudgetRowEditError, match="contrato editable"):
        BudgetRowEditService(OPEX_MODULE_CONFIG).edit_value(
            row, "row_id", "otro"
        )


def test_nonzero_annual_rejects_zero_basis():
    row = make_row(OPEX_MODULE_CONFIG)
    with pytest.raises(BudgetRowEditError, match="distribucion mensual previa"):
        BudgetRowEditService(OPEX_MODULE_CONFIG).edit_value(
            row, "anio_usd", "100"
        )
