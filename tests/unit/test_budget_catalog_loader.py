
import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.ui.workers.budget_catalog_loader import (
    catalog_columns_for_config,
)


pytestmark = pytest.mark.unit


def test_opex_catalog_columns():
    columns = (
        catalog_columns_for_config(
            OPEX_MODULE_CONFIG
        )
    )

    assert columns == (
        "pais",
        "presupuestador",
        "ceco",
        "moneda_facturacion",
        "compania",
    )


def test_capex_catalog_columns():
    columns = (
        catalog_columns_for_config(
            CAPEX_MODULE_CONFIG
        )
    )

    assert columns == (
        "pais",
        "presupuestador",
        "codigo_ceco",
        "moneda_facturacion",
        "sociedad",
        "responsable",
    )


def test_catalog_columns_have_no_duplicates():
    columns = (
        catalog_columns_for_config(
            OPEX_MODULE_CONFIG
        )
    )

    assert (
        len(columns)
        == len(set(columns))
    )
