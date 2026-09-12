from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.config.presupuesto_schema import (
    MONTHS,
)
from app.models.opex_fx import (
    OpexFxTable,
)
from app.models.opex_smart_enrichment import (
    OpexSmartEnrichedRow,
)
from app.models.opex_smart_periodization import (
    OpexSmartPeriodizedRow,
)
from app.services.opex_fx_service import (
    OpexFxError,
    OpexFxService,
)


pytestmark = pytest.mark.unit


def table():
    return OpexFxTable(
        year=2027,
        currency_per_usd={
            "USD":
                Decimal("1"),
            "PEN":
                Decimal("3.40"),
            "COP":
                Decimal("3300"),
            "BOB":
                Decimal("12"),
        },
        local_currency_by_country={
            "PE":
                "PEN",
            "CO":
                "COP",
            "BO":
                "BOB",
            "EC":
                "USD",
        },
    )


def service():
    return OpexFxService(
        table()
    )


def test_usd_invoice_in_peru():
    result = (
        service()
        .convert_month(
            mf_amount="100",
            invoice_currency="USD",
            country="PE",
        )
    )

    assert result == {
        "mf":
            Decimal("100.00"),
        "usd":
            Decimal("100.00"),
        "ml":
            Decimal("340.00"),
    }


def test_pen_invoice_in_peru():
    result = (
        service()
        .convert_month(
            mf_amount="340",
            invoice_currency="PEN",
            country="PE",
        )
    )

    assert result == {
        "mf":
            Decimal("340.00"),
        "usd":
            Decimal("100.00"),
        "ml":
            Decimal("340.00"),
    }


def test_local_currency_invoice_preserves_ml():
    result = (
        service()
        .convert_month(
            mf_amount="3300",
            invoice_currency="COP",
            country="CO",
        )
    )

    assert result == {
        "mf":
            Decimal("3300.00"),
        "usd":
            Decimal("1.00"),
        "ml":
            Decimal("3300.00"),
    }


def test_historical_cops_alias_uses_cop():
    result = (
        service()
        .convert_month(
            mf_amount="3300",
            invoice_currency="COPS",
            country="CO",
        )
    )

    assert result["usd"] == Decimal("1.00")
    assert result["ml"] == Decimal("3300.00")


def test_usd_country_keeps_usd_as_ml():
    result = (
        service()
        .convert_month(
            mf_amount="50",
            invoice_currency="USD",
            country="EC",
        )
    )

    assert result == {
        "mf":
            Decimal("50.00"),
        "usd":
            Decimal("50.00"),
        "ml":
            Decimal("50.00"),
    }


def test_missing_invoice_rate_is_blocked():
    with pytest.raises(
        OpexFxError,
        match="EUR",
    ):
        (
            service()
            .convert_month(
                mf_amount="100",
                invoice_currency="EUR",
                country="PE",
            )
        )


def test_missing_country_is_blocked():
    with pytest.raises(
        OpexFxError,
        match="CL",
    ):
        (
            service()
            .convert_month(
                mf_amount="100",
                invoice_currency="USD",
                country="CL",
            )
        )


def test_usd_rate_must_be_one():
    with pytest.raises(
        OpexFxError,
        match="USD",
    ):
        OpexFxService(
            OpexFxTable(
                year=2027,
                currency_per_usd={
                    "USD":
                        Decimal("0.99"),
                },
                local_currency_by_country={},
            )
        )


def test_wrong_year_is_rejected():
    with pytest.raises(
        OpexFxError,
        match="2027",
    ):
        OpexFxService(
            OpexFxTable(
                year=2026,
                currency_per_usd={
                    "USD":
                        Decimal("1"),
                },
                local_currency_by_country={},
            )
        )


def test_monthly_values_builds_all_36_columns():
    source = OpexSmartEnrichedRow(
        sheet_name="TEST",
        excel_row=8,
        nombre_gasto="GASTO",
        proveedor="PROVEEDOR",
        moneda_facturacion="USD",
        numero_cuenta="635610007",
        tipo="MENSUAL",
        monto_presupuesto=Decimal("100"),
        ceco="001234",
        monto_ceco=Decimal("100"),
        enrichment=(
            SimpleNamespace(
                pais="PE"
            )
        ),
    )

    periodized = OpexSmartPeriodizedRow(
        source_row=source,
        monthly_amounts=tuple(
            (
                month,
                Decimal("100")
            )
            for month in MONTHS
        ),
        annual_amount=Decimal("1200"),
    )

    result = (
        service()
        .monthly_values(
            periodized
        )
    )

    assert len(result) == 36

    for month in MONTHS:
        assert (
            result[
                f"{month}_mf"
            ]
            == Decimal("100.00")
        )

        assert (
            result[
                f"{month}_usd"
            ]
            == Decimal("100.00")
        )

        assert (
            result[
                f"{month}_ml"
            ]
            == Decimal("340.00")
        )
