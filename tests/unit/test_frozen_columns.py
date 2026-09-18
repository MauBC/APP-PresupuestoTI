import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.ui.frozen_columns import (
    resolve_frozen_columns,
)


pytestmark = pytest.mark.unit


def test_resolve_frozen_columns_preserves_preference_order():
    result = resolve_frozen_columns(
        columns=(
            "pais",
            "presupuestador",
            "nombre_inversion",
            "anio_usd",
        ),
        preferred_columns=(
            "presupuestador",
            "pais",
            "nombre_inversion",
        ),
    )

    assert result == (
        "presupuestador",
        "pais",
        "nombre_inversion",
    )


def test_resolve_frozen_columns_ignores_missing_and_duplicates():
    result = resolve_frozen_columns(
        columns=(
            "pais",
            "nombre_gasto",
        ),
        preferred_columns=(
            "pais",
            "no_existe",
            "pais",
            "nombre_gasto",
        ),
    )

    assert result == (
        "pais",
        "nombre_gasto",
    )


def test_opex_frozen_context_contract():
    assert (
        OPEX_MODULE_CONFIG
        .frozen_context_columns
        == (
            "presupuestador",
            "pais",
            "nombre_gasto",
        )
    )

    assert set(
        OPEX_MODULE_CONFIG
        .frozen_context_columns
    ).issubset(
        OPEX_MODULE_CONFIG
        .dimension_columns
    )


def test_capex_frozen_context_contract():
    assert (
        CAPEX_MODULE_CONFIG
        .frozen_context_columns
        == (
            "presupuestador",
            "pais",
            "nombre_inversion",
        )
    )

    assert set(
        CAPEX_MODULE_CONFIG
        .frozen_context_columns
    ).issubset(
        CAPEX_MODULE_CONFIG
        .dimension_columns
    )
