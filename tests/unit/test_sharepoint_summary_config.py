
import pytest

from app.config.sharepoint_summary_config import (
    CAPEX_SHAREPOINT_FIELDS,
)


pytestmark = pytest.mark.unit


def test_capex_sharepoint_contract_contains_key():
    assert (
        "SummaryKey"
        in CAPEX_SHAREPOINT_FIELDS
    )


def test_capex_sharepoint_contract_contains_total():
    assert (
        "TotalUSD"
        in CAPEX_SHAREPOINT_FIELDS
    )


def test_capex_sharepoint_contract_excludes_ceco():
    assert (
        "CodigoCECO"
        not in CAPEX_SHAREPOINT_FIELDS
    )

    assert (
        "CodigoCEBE"
        not in CAPEX_SHAREPOINT_FIELDS
    )
