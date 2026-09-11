from decimal import Decimal

import pytest

from app.ui.pages.dashboard_page import (
    build_monthly_chart_data,
    dashboard_month_label,
    format_monthly_bar_label_k,
    monthly_chart_axis_max_k,
)


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "column, expected",
    (
        (
            "enero_usd",
            "Enero",
        ),
        (
            "febrero_usd",
            "Febrero",
        ),
        (
            "setiembre_usd",
            "Setiembre",
        ),
        (
            "diciembre_usd",
            "Diciembre",
        ),
    ),
)
def test_dashboard_month_labels(
    column,
    expected,
):
    assert (
        dashboard_month_label(
            column
        )
        == expected
    )


def test_dashboard_month_label_has_safe_fallback():
    assert (
        dashboard_month_label(
            "mes_especial_usd"
        )
        == "Mes Especial"
    )


def test_dashboard_month_label_handles_none():
    assert (
        dashboard_month_label(
            None
        )
        == ""
    )


def test_monthly_chart_data_preserves_order():
    labels, values = (
        build_monthly_chart_data(
            (
                {
                    "column":
                        "enero_usd",
                    "total_usd":
                        Decimal(
                            "125000.00"
                        ),
                },
                {
                    "column":
                        "febrero_usd",
                    "total_usd":
                        Decimal(
                            "50000.00"
                        ),
                },
            )
        )
    )

    assert labels == (
        "Enero",
        "Febrero",
    )

    assert values == (
        125.0,
        50.0,
    )


def test_monthly_chart_data_handles_empty_amount():
    labels, values = (
        build_monthly_chart_data(
            (
                {
                    "column":
                        "marzo_usd",
                    "total_usd":
                        None,
                },
            )
        )
    )

    assert labels == (
        "Marzo",
    )

    assert values == (
        0.0,
    )


def test_monthly_chart_axis_uses_100k_headroom():
    assert (
        monthly_chart_axis_max_k(
            (
                125.0,
                500.0,
                800.0,
            )
        )
        == 900.0
    )


def test_monthly_chart_axis_rounds_then_adds_step():
    assert (
        monthly_chart_axis_max_k(
            (
                801.0,
            )
        )
        == 1000.0
    )


def test_monthly_chart_axis_handles_empty_values():
    assert (
        monthly_chart_axis_max_k(
            ()
        )
        == 100.0
    )


def test_monthly_bar_label_uses_thousands():
    assert (
        format_monthly_bar_label_k(
            423.4
        )
        == "423k"
    )


def test_monthly_bar_label_uses_separator():
    assert (
        format_monthly_bar_label_k(
            1250.4
        )
        == "1,250k"
    )


def test_monthly_bar_label_handles_zero():
    assert (
        format_monthly_bar_label_k(
            0
        )
        == "0k"
    )
