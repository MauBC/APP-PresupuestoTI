from decimal import Decimal

import pytest

from app.services.proportional_allocation_service import (
    ProportionalAllocationError,
    ProportionalAllocationService,
)


pytestmark = pytest.mark.unit


def test_proportional_allocation():
    result = (
        ProportionalAllocationService
        .allocate(
            (
                ("A", Decimal("30")),
                ("B", Decimal("70")),
            ),
            Decimal("200"),
        )
    )

    assert result == {
        "A": Decimal("60.00"),
        "B": Decimal("140.00"),
    }


def test_allocation_handles_cent_residual():
    result = (
        ProportionalAllocationService
        .allocate(
            (
                ("A", Decimal("1")),
                ("B", Decimal("1")),
                ("C", Decimal("1")),
            ),
            Decimal("10"),
        )
    )

    assert (
        sum(
            result.values(),
            Decimal("0")
        )
        == Decimal("10.00")
    )


def test_zero_target_sets_everything_to_zero():
    result = (
        ProportionalAllocationService
        .allocate(
            (
                ("A", Decimal("10")),
                ("B", Decimal("20")),
            ),
            Decimal("0"),
        )
    )

    assert result == {
        "A": Decimal("0.00"),
        "B": Decimal("0.00"),
    }


def test_zero_basis_cannot_receive_budget():
    with pytest.raises(
        ProportionalAllocationError
    ):
        (
            ProportionalAllocationService
            .allocate(
                (
                    ("A", Decimal("0")),
                    ("B", Decimal("0")),
                ),
                Decimal("100"),
            )
        )


def test_negative_source_is_rejected():
    with pytest.raises(
        ProportionalAllocationError
    ):
        (
            ProportionalAllocationService
            .allocate(
                (
                    ("A", Decimal("-1")),
                    ("B", Decimal("2")),
                ),
                Decimal("100"),
            )
        )
