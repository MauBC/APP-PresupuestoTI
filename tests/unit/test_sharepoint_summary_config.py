
import pytest

from app.config.sharepoint_summary_config import (
    CAPEX_SHAREPOINT_COLUMN_SPECS,
    CAPEX_SHAREPOINT_COMPARE_FIELDS,
    CAPEX_SHAREPOINT_FIELDS,
    CAPEX_SHAREPOINT_METADATA_FIELDS,
)


pytestmark = pytest.mark.unit


EXPECTED_CUSTOM_FIELDS = (
    "SummaryKey",
    "Vicepresidencia",
    "Pais",
    "Responsable",
    "GerenteAprobador",
    "TotalUSD",
    "SourceBatchId",
    "SyncRunId",
)


def test_capex_sharepoint_contract_is_minimal():
    assert tuple(
        spec.name
        for spec
        in CAPEX_SHAREPOINT_COLUMN_SPECS
    ) == EXPECTED_CUSTOM_FIELDS


def test_title_is_used_for_investment_name():
    assert (
        CAPEX_SHAREPOINT_FIELDS[0]
        == "Title"
    )

    assert (
        "NombreInversion"
        not in CAPEX_SHAREPOINT_FIELDS
    )


def test_removed_fields_are_not_in_contract():
    removed = {
        "Sociedad",
        "VPAprobador",
        "NombreInversion",
        "RegistrosOrigen",
        "UpdatedAt",
        "Modulo",
    }

    assert removed.isdisjoint(
        CAPEX_SHAREPOINT_FIELDS
    )


def test_compare_fields_only_contain_business_state():
    assert (
        CAPEX_SHAREPOINT_COMPARE_FIELDS
        == (
            "Title",
            "SummaryKey",
            "Vicepresidencia",
            "Pais",
            "Responsable",
            "GerenteAprobador",
            "TotalUSD",
        )
    )


def test_metadata_keeps_traceability():
    assert (
        CAPEX_SHAREPOINT_METADATA_FIELDS
        == (
            "SourceBatchId",
            "SyncRunId",
        )
    )
