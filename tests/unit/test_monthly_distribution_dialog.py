from decimal import Decimal

import pytest

from app.ui.dialogs.monthly_distribution_dialog import (
    build_current_percentages,
    build_equal_percentages,
)


pytestmark = pytest.mark.unit


MONTHS = (
    "m1",
    "m2",
    "m3",
)


def test_current_percentages_sum_exactly_100():
    row = {
        "m1": Decimal("10.00"),
        "m2": Decimal("20.00"),
        "m3": Decimal("30.00"),
    }

    result = build_current_percentages(
        row,
        MONTHS,
    )

    assert (
        sum(
            result.values(),
            Decimal("0")
        )
        == Decimal("100.00")
    )


def test_equal_distribution_handles_rounding():
    row = {
        "m1": Decimal("1.00"),
        "m2": Decimal("1.00"),
        "m3": Decimal("1.00"),
    }

    result = build_equal_percentages(
        row,
        MONTHS,
    )

    assert result == {
        "m1": Decimal("33.33"),
        "m2": Decimal("33.33"),
        "m3": Decimal("33.34"),
    }

    assert (
        sum(
            result.values(),
            Decimal("0")
        )
        == Decimal("100.00")
    )


def test_null_month_gets_zero_percent():
    row = {
        "m1": Decimal("10.00"),
        "m2": None,
        "m3": Decimal("30.00"),
    }

    result = build_current_percentages(
        row,
        MONTHS,
    )

    assert (
        result["m2"]
        == Decimal("0.00")
    )

    assert (
        result["m1"]
        + result["m3"]
        == Decimal("100.00")
    )
