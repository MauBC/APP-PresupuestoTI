
import pytest

from app.config.budget_module_config import (
    BudgetModule,
)
from app.config.budget_summary_config import (
    CAPEX_POWERAPPS_SUMMARY,
    get_budget_summary_definition,
)


pytestmark = pytest.mark.unit


EXPECTED_GROUP_BY = (
    "vicepresidencia",
    "pais",
    "responsable",
    "gerente_aprobador",
    "nombre_inversion",
)


def test_capex_powerapps_summary_uses_minimal_dimensions():
    assert (
        CAPEX_POWERAPPS_SUMMARY
        .group_by
        == EXPECTED_GROUP_BY
    )


def test_capex_summary_uses_annual_usd():
    assert (
        CAPEX_POWERAPPS_SUMMARY
        .amount_column
        == "anio_usd"
    )


def test_capex_summary_excludes_removed_dimensions():
    assert (
        "sociedad"
        not in CAPEX_POWERAPPS_SUMMARY
        .group_by
    )

    assert (
        "vp_aprobador"
        not in CAPEX_POWERAPPS_SUMMARY
        .group_by
    )

    assert (
        "codigo_ceco"
        not in CAPEX_POWERAPPS_SUMMARY
        .group_by
    )


def test_summary_registry_resolves_capex():
    result = (
        get_budget_summary_definition(
            BudgetModule.CAPEX,
            "capex_powerapps",
        )
    )

    assert (
        result
        is CAPEX_POWERAPPS_SUMMARY
    )
