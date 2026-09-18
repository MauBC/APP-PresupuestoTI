import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.services.budget_catalog_service import (
    BudgetCatalogError,
    BudgetCatalogService,
)


pytestmark = pytest.mark.unit


class FakeRepository:
    def __init__(
        self,
        module_config,
    ):
        self.module_config = (
            module_config
        )

        self.calls = []

    def get_catalog_values(
        self,
        column,
        *,
        filters=None,
        limit=500,
    ):
        self.calls.append(
            {
                "column":
                    column,
                "filters":
                    dict(
                        filters
                        or {}
                    ),
                "limit":
                    limit,
            }
        )

        data = {
            "pais":
                (
                    "CHL",
                    "PER",
                ),
            "compania":
                (
                    "Ransa Peru",
                ),
            "presupuestador":
                (
                    "Ana",
                    "Mauro",
                ),
            "responsable":
                (
                    "Mauro",
                ),
            "codigo_ceco":
                (
                    "001",
                    "002",
                ),
        }

        return data.get(
            column,
            (),
        )


def test_opex_catalog_uses_module_column():
    repository = FakeRepository(
        OPEX_MODULE_CONFIG
    )

    service = BudgetCatalogService(
        repository
    )

    result = service.values(
        "pais"
    )

    assert (
        result.values
        == (
            "CHL",
            "PER",
        )
    )

    assert (
        repository.calls[0]
        ["column"]
        == "pais"
    )


def test_catalog_keeps_cascade_filters():
    repository = FakeRepository(
        OPEX_MODULE_CONFIG
    )

    service = BudgetCatalogService(
        repository
    )

    result = service.values(
        "compania",
        filters={
            "pais": " PER ",
            "ceco": None,
        },
    )

    assert (
        result.filters
        == (
            (
                "pais",
                "PER",
            ),
        )
    )

    assert (
        repository.calls[0]
        ["filters"]
        == {
            "pais": "PER",
        }
    )


def test_capex_uses_presupuestador_as_budgeter():
    repository = FakeRepository(
        CAPEX_MODULE_CONFIG
    )

    service = BudgetCatalogService(
        repository
    )

    catalogs = (
        service.common_catalogs()
    )

    assert (
        "presupuestador"
        in catalogs
    )

    assert (
        "responsable"
        not in catalogs
    )

    assert (
        "codigo_ceco"
        in catalogs
    )


def test_invalid_catalog_column_is_rejected():
    repository = FakeRepository(
        CAPEX_MODULE_CONFIG
    )

    service = BudgetCatalogService(
        repository
    )

    with pytest.raises(
        BudgetCatalogError,
        match="no pertenece",
    ):
        service.values(
            "campo_inventado"
        )


def test_invalid_filter_is_rejected():
    repository = FakeRepository(
        OPEX_MODULE_CONFIG
    )

    service = BudgetCatalogService(
        repository
    )

    with pytest.raises(
        BudgetCatalogError,
        match="Filtro no valido",
    ):
        service.values(
            "pais",
            filters={
                "campo_inventado":
                    "x",
            },
        )
