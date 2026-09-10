
from decimal import Decimal

import pytest

from app.config.budget_summary_config import (
    CAPEX_POWERAPPS_SUMMARY,
)
from app.config.sharepoint_summary_config import (
    CAPEX_SHAREPOINT_BUSINESS_FIELDS,
    CAPEX_SHAREPOINT_COMPARE_FIELDS,
)
from app.models.budget_summary import (
    BudgetSummaryRow,
)
from app.services.sharepoint_summary_mapper import (
    SharePointSummaryMapper,
)


pytestmark = pytest.mark.unit


def mapper():
    return (
        SharePointSummaryMapper(
            field_mapping=(
                CAPEX_SHAREPOINT_BUSINESS_FIELDS
            ),
            compare_fields=(
                CAPEX_SHAREPOINT_COMPARE_FIELDS
            ),
            title_source=(
                "nombre_inversion"
            ),
            module="CAPEX",
        )
    )


def make_row():
    return (
        BudgetSummaryRow(
            summary_key="a" * 64,
            dimensions=(
                (
                    "vicepresidencia",
                    "TI",
                ),
                (
                    "pais",
                    "Peru",
                ),
                (
                    "sociedad",
                    "Ransa Comercial",
                ),
                (
                    "responsable",
                    "Ana",
                ),
                (
                    "gerente_aprobador",
                    "Gerente",
                ),
                (
                    "vp_aprobador",
                    "VP",
                ),
                (
                    "nombre_inversion",
                    "Proyecto A",
                ),
            ),
            registros_origen=3,
            total_usd=Decimal(
                "65000.25"
            ),
        )
    )


def test_maps_capex_summary_to_sharepoint():
    item = (
        mapper()
        .map_row(
            make_row()
        )
    )

    fields = (
        item.fields_dict()
    )

    assert (
        item.summary_key
        == "a" * 64
    )

    assert (
        fields["Title"]
        == "Proyecto A"
    )

    assert (
        fields["SummaryKey"]
        == "a" * 64
    )

    assert (
        fields["TotalUSD"]
        == 65000.25
    )

    assert (
        fields["RegistrosOrigen"]
        == 3
    )

    assert (
        fields["Modulo"]
        == "CAPEX"
    )

    assert (
        "CodigoCECO"
        not in fields
    )


def test_mapper_preserves_nullable_dimensions():
    row = make_row()

    dimensions = tuple(
        (
            name,
            (
                None
                if name == "responsable"
                else value
            ),
        )
        for name, value
        in row.dimensions
    )

    row = BudgetSummaryRow(
        summary_key=row.summary_key,
        dimensions=dimensions,
        registros_origen=(
            row.registros_origen
        ),
        total_usd=(
            row.total_usd
        ),
    )

    fields = (
        mapper()
        .map_row(
            row
        )
        .fields_dict()
    )

    assert (
        fields["Responsable"]
        is None
    )
