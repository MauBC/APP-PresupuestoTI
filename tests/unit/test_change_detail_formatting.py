from decimal import Decimal

import pytest

from app.ui.change_detail_formatting import (
    change_amount_unit,
    change_field_label,
    format_change_difference,
    format_change_value,
)


pytestmark = pytest.mark.unit


def test_usd_amount_format():
    assert (
        format_change_value(
            "enero_usd",
            Decimal("1234.5"),
        )
        == "US$ 1,234.50"
    )

    assert (
        format_change_difference(
            "enero_usd",
            Decimal("25.5"),
        )
        == "+US$ 25.50"
    )


def test_ml_amount_format():
    assert (
        format_change_value(
            "enero_ml",
            Decimal("1234.5"),
        )
        == "ML 1,234.50"
    )

    assert (
        format_change_difference(
            "enero_ml",
            Decimal("-20"),
        )
        == "-ML 20.00"
    )


def test_mf_amount_format():
    assert (
        format_change_value(
            "enero_mf",
            Decimal("45.25"),
        )
        == "MF 45.25"
    )

    assert (
        format_change_difference(
            "enero_mf",
            Decimal("5"),
        )
        == "+MF 5.00"
    )


def test_enabled_difference_is_annual_usd():
    assert (
        change_amount_unit(
            "habilitado"
        )
        == "US$"
    )

    assert (
        format_change_difference(
            "habilitado",
            Decimal("-100"),
        )
        == "-US$ 100.00"
    )


def test_boolean_state_format():
    assert (
        format_change_value(
            "habilitado",
            True,
        )
        == "Habilitado"
    )

    assert (
        format_change_value(
            "habilitado",
            False,
        )
        == "Deshabilitado"
    )


def test_business_field_labels():
    assert (
        change_field_label(
            "codigo_ceco"
        )
        == "Codigo CECO"
    )

    assert (
        change_field_label(
            "codigo_cebe"
        )
        == "Codigo CEBE"
    )

    assert (
        change_field_label(
            "anio_usd"
        )
        == "Total Anual USD"
    )
