
import pytest

from app.config.budget_summary_config import (
    CAPEX_POWERAPPS_SUMMARY,
)


pytestmark = pytest.mark.unit


def test_capex_powerapps_contract():
    definition = (
        CAPEX_POWERAPPS_SUMMARY
    )

    assert definition.module == "CAPEX"

    assert definition.group_by == (
        "vicepresidencia",
        "pais",
        "sociedad",
        "responsable",
        "gerente_aprobador",
        "vp_aprobador",
        "nombre_inversion",
    )

    assert (
        definition.amount_column
        == "anio_usd"
    )


def test_capex_summary_excludes_ceco():
    definition = (
        CAPEX_POWERAPPS_SUMMARY
    )

    assert (
        "codigo_ceco"
        not in definition.group_by
    )

    assert (
        "codigo_cebe"
        not in definition.group_by
    )
