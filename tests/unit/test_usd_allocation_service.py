from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.services.usd_allocation_service import (
    UsdAllocationError,
    UsdAllocationService,
)


pytestmark = pytest.mark.unit


def make_row():
    row = {
        column: Decimal("0.00")
        for column in USD_MONTH_COLUMNS
    }

    row["enero_usd"] = Decimal("10.00")
    row["febrero_usd"] = Decimal("30.00")
    row["anio_usd"] = Decimal("40.00")

    return row


def test_calculate_total_uses_months():
    row = make_row()

    result = (
        UsdAllocationService.calculate_total(
            row
        )
    )

    assert result == Decimal("40.00")


def test_month_edit_recalculates_annual_total():
    row = make_row()

    result = UsdAllocationService.set_month(
        row,
        "enero_usd",
        Decimal("20.00"),
    )

    assert (
        result["enero_usd"]
        == Decimal("20.00")
    )

    assert (
        result["febrero_usd"]
        == Decimal("30.00")
    )

    assert (
        result["anio_usd"]
        == Decimal("50.00")
    )


def test_annual_edit_preserves_proportion():
    row = make_row()

    result = (
        UsdAllocationService.set_annual_total(
            row,
            Decimal("80.00"),
        )
    )

    assert (
        result["enero_usd"]
        == Decimal("20.00")
    )

    assert (
        result["febrero_usd"]
        == Decimal("60.00")
    )

    assert (
        result["anio_usd"]
        == Decimal("80.00")
    )


def test_annual_edit_uses_month_sum_as_basis():
    row = make_row()

    row["anio_usd"] = Decimal("40.04")

    result = (
        UsdAllocationService.set_annual_total(
            row,
            Decimal("80.00"),
        )
    )

    assert (
        result["enero_usd"]
        == Decimal("20.00")
    )

    assert (
        result["febrero_usd"]
        == Decimal("60.00")
    )

    assert (
        result["anio_usd"]
        == Decimal("80.00")
    )


def test_annual_distribution_handles_rounding():
    row = {
        column: Decimal("0.00")
        for column in USD_MONTH_COLUMNS
    }

    row["enero_usd"] = Decimal("1.00")
    row["febrero_usd"] = Decimal("1.00")
    row["marzo_usd"] = Decimal("1.00")
    row["anio_usd"] = Decimal("3.00")

    result = (
        UsdAllocationService.set_annual_total(
            row,
            Decimal("10.00"),
        )
    )

    assert (
        UsdAllocationService.calculate_total(
            result
        )
        == Decimal("10.00")
    )

    assert (
        result["anio_usd"]
        == Decimal("10.00")
    )


def test_zero_total_cannot_be_scaled_to_nonzero():
    row = {
        column: Decimal("0.00")
        for column in USD_MONTH_COLUMNS
    }

    row["anio_usd"] = Decimal("0.00")

    with pytest.raises(
        UsdAllocationError
    ):
        UsdAllocationService.set_annual_total(
            row,
            Decimal("100.00"),
        )


def test_negative_month_is_rejected():
    row = make_row()

    with pytest.raises(
        UsdAllocationError
    ):
        UsdAllocationService.set_month(
            row,
            "enero_usd",
            Decimal("-1.00"),
        )


def test_original_row_is_not_modified():
    row = make_row()

    original = dict(row)

    UsdAllocationService.set_annual_total(
        row,
        Decimal("80.00"),
    )

    assert row == original