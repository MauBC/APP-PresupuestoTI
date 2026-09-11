from decimal import Decimal

import pytest

from app.ui.dialogs.dimension_allocation_dialog import (
    build_equal_percentages,
)


pytestmark = pytest.mark.unit


def test_equal_dimension_distribution_is_exact():
    result = (
        build_equal_percentages(
            (
                "A",
                "B",
                "C",
            )
        )
    )

    assert result == {
        "A": Decimal("33.33"),
        "B": Decimal("33.33"),
        "C": Decimal("33.34"),
    }

    assert (
        sum(
            result.values(),
            Decimal("0")
        )
        == Decimal("100.00")
    )
