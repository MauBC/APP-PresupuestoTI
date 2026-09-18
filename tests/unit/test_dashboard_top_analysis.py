from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.config.budget_module_config import (
    BudgetModule,
)
from app.ui.pages.dashboard_page import (
    build_dashboard_top_chart_data,
    build_dashboard_top_rows,
    dashboard_dimension_label,
    dashboard_top_axis_max_k,
    dashboard_top_chart_label,
    dashboard_top_dimension_options,
)


pytestmark = pytest.mark.unit


def test_opex_top_dimensions_follow_available_contract():
    config = SimpleNamespace(
        module=BudgetModule.OPEX,
        groupable_columns=(
            "pais",
            "proveedor",
            "nombre_gasto",
            "origen",
        ),
    )

    assert (
        dashboard_top_dimension_options(
            config
        )
        == (
            "pais",
            "proveedor",
            "nombre_gasto",
        )
    )


def test_capex_top_dimensions_follow_available_contract():
    config = SimpleNamespace(
        module=BudgetModule.CAPEX,
        groupable_columns=(
            "vicepresidencia",
            "pais",
            "codigo_ceco",
            "cantidad",
        ),
    )

    assert (
        dashboard_top_dimension_options(
            config
        )
        == (
            "pais",
            "vicepresidencia",
            "codigo_ceco",
        )
    )


def test_top_rows_are_sorted_limited_and_participated():
    rows = (
        {
            "proveedor": "B",
            "registros": 3,
            "total_usd": Decimal("300"),
        },
        {
            "proveedor": "A",
            "registros": 5,
            "total_usd": Decimal("500"),
        },
        {
            "proveedor": "C",
            "registros": 2,
            "total_usd": Decimal("200"),
        },
    )

    result = build_dashboard_top_rows(
        rows,
        dimension="proveedor",
        top_n=2,
        total_usd=Decimal("1000"),
    )

    assert len(result) == 2

    assert (
        result[0]["proveedor"]
        == "A"
    )

    assert (
        result[0]["total_usd"]
        == Decimal("500")
    )

    assert (
        result[0]["participacion_pct"]
        == Decimal("50.00")
    )

    assert (
        result[1]["proveedor"]
        == "B"
    )

    assert (
        result[1]["participacion_pct"]
        == Decimal("30.00")
    )


def test_top_rows_handle_zero_total():
    rows = (
        {
            "pais": "PE",
            "registros": 1,
            "total_usd": Decimal("0"),
        },
    )

    result = build_dashboard_top_rows(
        rows,
        dimension="pais",
        top_n=10,
        total_usd=Decimal("0"),
    )

    assert (
        result[0]["participacion_pct"]
        == Decimal("0.00")
    )


def test_dashboard_dimension_labels_use_business_names():
    assert (
        dashboard_dimension_label(
            "codigo_ceco"
        )
        == "Codigo CECO"
    )

    assert (
        dashboard_dimension_label(
            "nombre_inversion"
        )
        == "Nombre de inversion"
    )

    assert (
        dashboard_dimension_label(
            "proveedor"
        )
        == "Proveedor"
    )

def test_top_chart_label_truncates_long_values():
    value = dashboard_top_chart_label(
        "Proveedor con un nombre extremadamente largo",
        max_length=20,
    )

    assert len(value) == 20
    assert value.endswith("...")


def test_top_chart_data_reverses_rows_for_horizontal_chart():
    rows = (
        {
            "proveedor": "Mayor",
            "registros": 5,
            "total_usd": Decimal("500000"),
            "participacion_pct":
                Decimal("50.00"),
        },
        {
            "proveedor": "Menor",
            "registros": 2,
            "total_usd": Decimal("200000"),
            "participacion_pct":
                Decimal("20.00"),
        },
    )

    result = build_dashboard_top_chart_data(
        rows,
        dimension="proveedor",
    )

    assert result["labels"] == (
        "Menor",
        "Mayor",
    )

    assert result["values_k"] == (
        200.0,
        500.0,
    )

    assert "US$ 500,000.00" in (
        result["tooltips"][1]
    )

    assert "50.00%" in (
        result["tooltips"][1]
    )

    assert "5 registros" in (
        result["tooltips"][1]
    )


def test_top_axis_adds_visual_headroom():
    assert (
        dashboard_top_axis_max_k(
            (100.0, 200.0)
        )
        == pytest.approx(
            230.0
        )
    )

    assert (
        dashboard_top_axis_max_k(
            ()
        )
        == 1.0
    )
