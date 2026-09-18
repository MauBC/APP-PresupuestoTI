from decimal import Decimal

import pytest

from app.config.presupuesto_schema import (
    MONTHS,
)
from app.models.opex_smart_enrichment import (
    OpexSmartEnrichedRow,
)
from app.services.opex_smart_periodization_service import (
    OpexSmartPeriodizationError,
    OpexSmartPeriodizationService,
)


pytestmark = pytest.mark.unit


def row(
    *,
    tipo,
    monto_ceco,
    ceco="001234",
):
    return OpexSmartEnrichedRow(
        sheet_name="TEST",
        excel_row=8,
        nombre_gasto="GASTO",
        proveedor="PROVEEDOR",
        moneda_facturacion="USD",
        numero_cuenta="635610007",
        tipo=tipo,
        monto_presupuesto=Decimal("1000"),
        ceco=ceco,
        monto_ceco=Decimal(
            str(monto_ceco)
        ),
        enrichment=None,
    )


def test_monthly_amount_is_repeated_each_month():
    result = (
        OpexSmartPeriodizationService
        .periodize_row(
            row(
                tipo="MENSUAL",
                monto_ceco="100.25",
            )
        )
    )

    monthly = result.monthly_map()

    assert tuple(
        monthly
    ) == MONTHS

    assert all(
        amount
        == Decimal("100.25")
        for amount
        in monthly.values()
    )

    assert (
        result.annual_amount
        == Decimal("1203.00")
    )


def test_annual_amount_is_split_between_twelve_months():
    result = (
        OpexSmartPeriodizationService
        .periodize_row(
            row(
                tipo="ANUAL",
                monto_ceco="1000",
            )
        )
    )

    monthly = result.monthly_map()

    assert tuple(
        monthly
    ) == MONTHS

    assert len(
        monthly
    ) == 12

    assert (
        sum(
            monthly.values(),
            Decimal("0.00"),
        )
        == Decimal("1000.00")
    )

    assert (
        result.annual_amount
        == Decimal("1000.00")
    )

    assert (
        max(
            monthly.values()
        )
        - min(
            monthly.values()
        )
        <= Decimal("0.01")
    )


def test_annual_distribution_preserves_cents_exactly():
    result = (
        OpexSmartPeriodizationService
        .periodize_row(
            row(
                tipo="ANUAL",
                monto_ceco="100.01",
            )
        )
    )

    assert (
        sum(
            result.monthly_map().values(),
            Decimal("0.00"),
        )
        == Decimal("100.01")
    )

    assert (
        result.annual_amount
        == Decimal("100.01")
    )


def test_zero_annual_amount_produces_zero_months():
    result = (
        OpexSmartPeriodizationService
        .periodize_row(
            row(
                tipo="ANUAL",
                monto_ceco="0",
            )
        )
    )

    assert all(
        amount
        == Decimal("0.00")
        for amount
        in result.monthly_map().values()
    )

    assert (
        result.annual_amount
        == Decimal("0.00")
    )


def test_invalid_tipo_is_rejected():
    with pytest.raises(
        OpexSmartPeriodizationError,
        match="ANUAL o MENSUAL",
    ):
        (
            OpexSmartPeriodizationService
            .periodize_row(
                row(
                    tipo="SEMANAL",
                    monto_ceco="100",
                )
            )
        )


def test_negative_amount_is_rejected():
    with pytest.raises(
        OpexSmartPeriodizationError,
        match="negativo",
    ):
        (
            OpexSmartPeriodizationService
            .periodize_row(
                row(
                    tipo="ANUAL",
                    monto_ceco="-1",
                )
            )
        )


def test_periodize_rows_preserves_order():
    source = (
        row(
            tipo="ANUAL",
            monto_ceco="120",
            ceco="A",
        ),
        row(
            tipo="MENSUAL",
            monto_ceco="20",
            ceco="B",
        ),
    )

    result = (
        OpexSmartPeriodizationService
        .periodize_rows(
            source
        )
    )

    assert tuple(
        item.source_row.ceco
        for item
        in result
    ) == (
        "A",
        "B",
    )

    assert (
        result[0].annual_amount
        == Decimal("120.00")
    )

    assert (
        result[1].annual_amount
        == Decimal("240.00")
    )
