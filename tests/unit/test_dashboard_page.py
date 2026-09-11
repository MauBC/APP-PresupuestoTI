from decimal import Decimal

import pytest

from app.ui.pages.dashboard_page import (
    build_monthly_chart_data,
    compare_dashboard_months,
    comparison_visual_state,
    dashboard_filter_status_text,
    dashboard_has_active_filters,
    dashboard_month_label,
    dashboard_peak_month,
    format_monthly_bar_label_k,
    format_monthly_bar_tooltip,
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



def test_monthly_bar_tooltip_shows_full_usd_value():
    assert (
        format_monthly_bar_tooltip(
            "Marzo",
            Decimal(
                "583421.27"
            ),
        )
        == (
            "Marzo\n"
            "US$ 583,421.27"
        )
    )


def test_monthly_bar_tooltip_handles_zero():
    assert (
        format_monthly_bar_tooltip(
            "Abril",
            Decimal("0"),
        )
        == (
            "Abril\n"
            "US$ 0.00"
        )
    )


def test_monthly_bar_tooltip_handles_none():
    assert (
        format_monthly_bar_tooltip(
            "Mayo",
            None,
        )
        == (
            "Mayo\n"
            "US$ 0.00"
        )
    )



def test_dashboard_peak_month_uses_highest_total():
    month, amount = dashboard_peak_month(
        (
            {
                "column":
                    "enero_usd",
                "total_usd":
                    Decimal("100"),
            },
            {
                "column":
                    "febrero_usd",
                "total_usd":
                    Decimal("250"),
            },
            {
                "column":
                    "marzo_usd",
                "total_usd":
                    Decimal("180"),
            },
        )
    )

    assert month == "Febrero"
    assert amount == Decimal("250")


def test_dashboard_peak_month_keeps_first_month_on_tie():
    month, amount = dashboard_peak_month(
        (
            {
                "column":
                    "enero_usd",
                "total_usd":
                    Decimal("100"),
            },
            {
                "column":
                    "febrero_usd",
                "total_usd":
                    Decimal("100"),
            },
        )
    )

    assert month == "Enero"
    assert amount == Decimal("100")


def test_dashboard_peak_month_handles_empty_data():
    assert (
        dashboard_peak_month(
            ()
        )
        == (
            "",
            Decimal("0"),
        )
    )


def test_month_comparison_calculates_difference_and_variation():
    result = compare_dashboard_months(
        (
            {
                "column":
                    "enero_usd",
                "total_usd":
                    Decimal("100"),
            },
            {
                "column":
                    "febrero_usd",
                "total_usd":
                    Decimal("125"),
            },
        ),
        "enero_usd",
        "febrero_usd",
    )

    assert (
        result["base_usd"]
        == Decimal("100")
    )

    assert (
        result["target_usd"]
        == Decimal("125")
    )

    assert (
        result["difference_usd"]
        == Decimal("25")
    )

    assert (
        result["variation_percent"]
        == Decimal("25.00")
    )


def test_month_comparison_supports_decrease():
    result = compare_dashboard_months(
        (
            {
                "column":
                    "enero_usd",
                "total_usd":
                    Decimal("200"),
            },
            {
                "column":
                    "febrero_usd",
                "total_usd":
                    Decimal("150"),
            },
        ),
        "enero_usd",
        "febrero_usd",
    )

    assert (
        result["difference_usd"]
        == Decimal("-50")
    )

    assert (
        result["variation_percent"]
        == Decimal("-25.00")
    )


def test_month_comparison_marks_zero_base_as_not_defined():
    result = compare_dashboard_months(
        (
            {
                "column":
                    "enero_usd",
                "total_usd":
                    Decimal("0"),
            },
            {
                "column":
                    "febrero_usd",
                "total_usd":
                    Decimal("100"),
            },
        ),
        "enero_usd",
        "febrero_usd",
    )

    assert (
        result["variation_percent"]
        is None
    )


def test_month_comparison_zero_to_zero_is_zero_percent():
    result = compare_dashboard_months(
        (
            {
                "column":
                    "enero_usd",
                "total_usd":
                    Decimal("0"),
            },
            {
                "column":
                    "febrero_usd",
                "total_usd":
                    Decimal("0"),
            },
        ),
        "enero_usd",
        "febrero_usd",
    )

    assert (
        result["variation_percent"]
        == Decimal("0.00")
    )



def test_comparison_visual_state_increase():
    assert (
        comparison_visual_state(
            Decimal("10")
        )
        == "increase"
    )


def test_comparison_visual_state_decrease():
    assert (
        comparison_visual_state(
            Decimal("-10")
        )
        == "decrease"
    )


def test_comparison_visual_state_neutral():
    assert (
        comparison_visual_state(
            Decimal("0")
        )
        == "neutral"
    )



def test_dashboard_has_no_active_filters():
    assert not dashboard_has_active_filters(
        None,
        None,
    )


def test_dashboard_detects_country_filter():
    assert dashboard_has_active_filters(
        "PERU",
        None,
    )


def test_dashboard_detects_budgeter_filter():
    assert dashboard_has_active_filters(
        None,
        "ANA",
    )


def test_dashboard_filter_status_without_filters():
    assert (
        dashboard_filter_status_text(
            None,
            None,
            "Presupuestador",
        )
        == (
            "Dashboard calculado con "
            "los datos locales."
        )
    )


def test_dashboard_filter_status_with_opex_filters():
    assert (
        dashboard_filter_status_text(
            "PERU",
            "ANA",
            "Presupuestador",
        )
        == (
            "Dashboard calculado | "
            "País: PERU | "
            "Presupuestador: ANA"
        )
    )


def test_dashboard_filter_status_with_capex_responsable():
    assert (
        dashboard_filter_status_text(
            "PER",
            "Beatriz",
            "Responsable",
        )
        == (
            "Dashboard calculado | "
            "País: PER | "
            "Responsable: Beatriz"
        )
    )
