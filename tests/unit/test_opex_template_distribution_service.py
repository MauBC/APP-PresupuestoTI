from decimal import Decimal

import pytest

from app.models.opex_smart_template import (
    OpexTemplateBudget,
    OpexTemplateDistribution,
)
from app.services.opex_template_distribution_service import (
    OpexTemplateDistributionError,
    OpexTemplateDistributionService,
)


pytestmark = pytest.mark.unit


def item(
    ceco,
    *,
    percentage=None,
    amount=None,
):
    return OpexTemplateDistribution(
        excel_row=8,
        ceco=ceco,
        percentage=(
            Decimal(
                str(
                    percentage
                )
            )
            if percentage
            is not None
            else None
        ),
        amount=(
            Decimal(
                str(
                    amount
                )
            )
            if amount
            is not None
            else None
        ),
    )


def budget(
    *,
    monto="30000",
    rows=None,
):
    return OpexTemplateBudget(
        sheet_name="TEST",
        nombre_gasto="GASTO",
        proveedor="PROVEEDOR",
        moneda_facturacion="USD",
        numero_cuenta="635610007",
        tipo="MENSUAL",
        monto=Decimal(
            monto
        ),
        distributions=tuple(
            rows
            or ()
        ),
    )


def test_percentage_distribution_reuses_exact_allocation():
    value = budget(
        rows=(
            item(
                "A",
                percentage="0.40",
            ),
            item(
                "B",
                percentage="0.35",
            ),
            item(
                "C",
                percentage="0.25",
            ),
        )
    )

    result = (
        OpexTemplateDistributionService
        .resolve_percentages(
            value,
            {
                "A": "40",
                "B": "35",
                "C": "25",
            },
        )
    )

    assert result.amount_map() == {
        "A":
            Decimal("12000.00"),
        "B":
            Decimal("10500.00"),
        "C":
            Decimal("7500.00"),
    }

    assert (
        result.total
        == Decimal("30000.00")
    )


def test_percentage_must_equal_100():
    value = budget(
        rows=(
            item(
                "A",
                percentage="0.50",
            ),
            item(
                "B",
                percentage="0.50",
            ),
        )
    )

    with pytest.raises(
        OpexTemplateDistributionError,
        match="exceso",
    ):
        (
            OpexTemplateDistributionService
            .resolve_percentages(
                value,
                {
                    "A": "50",
                    "B": "50.01",
                },
            )
        )


def test_amount_distribution_uses_importes_as_weights():
    value = budget(
        monto="30000",
        rows=(
            item(
                "A",
                amount="100",
            ),
            item(
                "B",
                amount="200",
            ),
        )
    )

    result = (
        OpexTemplateDistributionService
        .resolve_amounts(
            value,
            {
                "A": "100",
                "B": "200",
            },
        )
    )

    assert result.amount_map() == {
        "A":
            Decimal("10000.00"),
        "B":
            Decimal("20000.00"),
    }

    assert (
        result.total
        == Decimal("30000.00")
    )


def test_amount_distribution_rejects_zero_weight():
    value = budget(
        monto="30000",
        rows=(
            item(
                "A",
                amount="0",
            ),
            item(
                "B",
                amount="0",
            ),
        )
    )

    with pytest.raises(
        OpexTemplateDistributionError,
        match="mayor que 0",
    ):
        (
            OpexTemplateDistributionService
            .resolve_amounts(
                value,
                {
                    "A": "0",
                    "B": "0",
                },
            )
        )


def test_amount_distribution_valid_when_exact():
    value = budget(
        monto="300",
        rows=(
            item(
                "A",
                amount="100",
            ),
            item(
                "B",
                amount="200",
            ),
        )
    )

    result = (
        OpexTemplateDistributionService
        .resolve_amounts(
            value,
            {
                "A": "100",
                "B": "200",
            },
        )
    )

    assert (
        result.total
        == Decimal("300.00")
    )


def test_rebalance_amounts_preserves_proportions():
    value = budget(
        monto="600",
        rows=(
            item(
                "A",
                amount="100",
            ),
            item(
                "B",
                amount="200",
            ),
        )
    )

    result = (
        OpexTemplateDistributionService
        .rebalance_amounts(
            value,
            {
                "A": "100",
                "B": "200",
            },
        )
    )

    assert result.amount_map() == {
        "A":
            Decimal("200.00"),
        "B":
            Decimal("400.00"),
    }

    assert (
        result.total
        == Decimal("600.00")
    )


def test_residual_never_loses_money():
    value = budget(
        monto="100",
        rows=(
            item(
                "A",
                percentage="0.3333",
            ),
            item(
                "B",
                percentage="0.3333",
            ),
            item(
                "C",
                percentage="0.3334",
            ),
        )
    )

    result = (
        OpexTemplateDistributionService
        .resolve_percentages(
            value,
            {
                "A": "33.33",
                "B": "33.33",
                "C": "33.34",
            },
        )
    )

    assert (
        result.total
        == Decimal("100.00")
    )


def test_inspect_accepts_amount_weights_when_raw_total_differs():
    value = budget(
        rows=(
            item(
                "A",
                percentage="0.5001",
                amount="100",
            ),
            item(
                "B",
                percentage="0.50",
                amount="200",
            ),
        )
    )

    result = (
        OpexTemplateDistributionService
        .inspect(
            value
        )
    )

    assert (
        result.available_modes
        == (
            "PORCENTAJE",
            "IMPORTE",
        )
    )

    assert (
        result.requires_mode_selection
        is True
    )

    assert (
        result.percentage_valid
        is False
    )

    assert (
        result.amount_valid
        is True
    )

    assert (
        result.requires_correction
        is False
    )


def test_percentage_only_does_not_require_mode_selection():
    value = budget(
        rows=(
            item(
                "A",
                percentage="0.40",
            ),
            item(
                "B",
                percentage="0.60",
            ),
        )
    )

    result = (
        OpexTemplateDistributionService
        .inspect(
            value
        )
    )

    assert (
        result.available_modes
        == (
            "PORCENTAJE",
        )
    )

    assert (
        result.requires_mode_selection
        is False
    )

    assert (
        result.percentage_valid
        is True
    )
