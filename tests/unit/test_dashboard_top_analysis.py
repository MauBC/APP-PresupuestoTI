from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.config.budget_module_config import (
    BudgetModule,
)
from app.ui.pages.dashboard_page import (
    build_dashboard_top_rows,
    dashboard_dimension_label,
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
