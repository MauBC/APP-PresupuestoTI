from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.config.new_budget_row_form import (
    get_new_budget_row_form,
)
from app.config.presupuesto_schema import (
    AMOUNT_GROUPS,
    MONTHS,
)
from app.services.new_budget_row_service import (
    NewBudgetRowService,
)
from app.services.opex_new_row_amount_service import (
    OpexNewRowAmountError,
    OpexNewRowAmountService,
    clean_opex_new_row_amount,
)


pytestmark = pytest.mark.unit


NOW = datetime(
    2026,
    9,
    11,
    21,
    0,
    tzinfo=timezone.utc,
)


def dimensions():
    return {
        "origen":
            "APP",
        "periodo":
            "2027",
        "presupuestador":
            "MAURO TEST",
        "pais":
            "PER",
        "compania":
            "RANSA PERU",
        "moneda_facturacion":
            "USD",
        "ceco":
            "001234",
        "centro_beneficio":
            "000456",
        "numero_cuenta":
            "000789",
        "nombre_cuenta":
            "SERVICIOS TI",
        "gyp":
            "TI",
        "desc_cebe":
            "CEBE TEST",
        "macroservicio_cg":
            "TECNOLOGIA",
        "tipo_servicio_cg":
            "SOFTWARE",
        "sede_cg":
            "LIMA",
        "region_cg":
            "PERU",
        "nombre_gasto":
            "TEST OPEX MANUAL",
        "proveedor":
            "PROVEEDOR TEST",
        "categoria_gasto":
            "SOFTWARE",
        "atributo_2":
            "TEST",
        "segmentacion":
            "TI",
    }


def make_draft():
    return (
        NewBudgetRowService(
            OPEX_MODULE_CONFIG,
            row_id_factory=(
                lambda:
                    "opex-manual-test"
            ),
        )
        .create_draft(
            dimensions(),
            actor="tester",
            timestamp=NOW,
        )
    )


def zero_months():
    return {
        f"{month}_{group}":
            "0"
        for group in AMOUNT_GROUPS
        for month in MONTHS
    }


def test_opex_form_has_business_sections():
    definition = (
        get_new_budget_row_form(
            OPEX_MODULE_CONFIG
        )
    )

    titles = tuple(
        section.title
        for section in (
            definition.sections
        )
    )

    assert titles == (
        "Datos generales",
        "Imputacion contable",
        "Centro de gestion",
        "Gasto y clasificacion",
    )


def test_opex_form_covers_all_dimensions_once():
    definition = (
        get_new_budget_row_form(
            OPEX_MODULE_CONFIG
        )
    )

    assert (
        set(
            definition.columns
        )
        ==
        set(
            OPEX_MODULE_CONFIG
            .dimension_columns
        )
    )

    assert (
        len(
            definition.columns
        )
        ==
        len(
            set(
                definition.columns
            )
        )
    )


def test_manual_amounts_cover_three_families():
    values = zero_months()

    values["enero_mf"] = "100"
    values["febrero_mf"] = "50.25"

    values["enero_usd"] = "40"
    values["febrero_usd"] = "60"

    values["enero_ml"] = "150"
    values["febrero_ml"] = "250"

    result = (
        OpexNewRowAmountService()
        .apply(
            make_draft(),
            monthly_values=values,
        )
    )

    assert (
        result.row["anio_mf"]
        == Decimal("150.25")
    )

    assert (
        result.row["anio_usd"]
        == Decimal("100.00")
    )

    assert (
        result.row["anio_ml"]
        == Decimal("400.00")
    )


def test_totals_are_always_derived_from_months():
    values = zero_months()

    for group in AMOUNT_GROUPS:
        values[
            f"enero_{group}"
        ] = "10.10"

        values[
            f"febrero_{group}"
        ] = "20.20"

    result = (
        OpexNewRowAmountService()
        .apply(
            make_draft(),
            monthly_values=values,
        )
    )

    for group in AMOUNT_GROUPS:
        total = sum(
            (
                result.row[
                    f"{month}_{group}"
                ]
                for month in MONTHS
            ),
            Decimal("0"),
        )

        assert (
            result.row[
                f"anio_{group}"
            ]
            == total
            == Decimal("30.30")
        )


def test_blank_amount_is_zero():
    assert (
        clean_opex_new_row_amount(
            ""
        )
        == Decimal("0.00")
    )

    assert (
        clean_opex_new_row_amount(
            None
        )
        == Decimal("0.00")
    )


def test_opex_amount_precision_is_two_decimals():
    assert (
        clean_opex_new_row_amount(
            "10.126"
        )
        == Decimal("10.13")
    )


def test_common_numeric_formats_are_supported():
    assert (
        clean_opex_new_row_amount(
            "1,234.56"
        )
        == Decimal("1234.56")
    )

    assert (
        clean_opex_new_row_amount(
            "1.234,56"
        )
        == Decimal("1234.56")
    )

    assert (
        clean_opex_new_row_amount(
            "US$ 125.50"
        )
        == Decimal("125.50")
    )


def test_negative_amount_is_rejected():
    with pytest.raises(
        OpexNewRowAmountError,
        match="negativo",
    ):
        clean_opex_new_row_amount(
            "-1"
        )


def test_missing_month_is_rejected():
    values = zero_months()

    del values[
        "diciembre_usd"
    ]

    with pytest.raises(
        OpexNewRowAmountError,
        match="Faltan",
    ):
        (
            OpexNewRowAmountService()
            .apply(
                make_draft(),
                monthly_values=values,
            )
        )


def test_ceco_leading_zeroes_are_preserved():
    result = (
        OpexNewRowAmountService()
        .apply(
            make_draft(),
            monthly_values=(
                zero_months()
            ),
        )
    )

    assert (
        result.row["ceco"]
        == "001234"
    )

    assert (
        result.row[
            "centro_beneficio"
        ]
        == "000456"
    )

    assert (
        result.row[
            "numero_cuenta"
        ]
        == "000789"
    )


def test_technical_metadata_is_preserved():
    result = (
        OpexNewRowAmountService()
        .apply(
            make_draft(),
            monthly_values=(
                zero_months()
            ),
        )
    )

    assert (
        result.row["row_id"]
        == "opex-manual-test"
    )

    assert result.row["version"] == 1
    assert result.row["habilitado"] is True

    assert (
        result.row["created_at"]
        == NOW
    )

    assert (
        result.row["created_by"]
        == "tester"
    )


def test_capex_draft_is_rejected():
    draft = (
        NewBudgetRowService(
            CAPEX_MODULE_CONFIG,
            row_id_factory=(
                lambda:
                    "capex-test"
            ),
        )
        .create_draft(
            {
                "anio":
                    2027,
                "cantidad":
                    1,
                "pais":
                    "PER",
            },
            actor="tester",
            timestamp=NOW,
        )
    )

    with pytest.raises(
        OpexNewRowAmountError,
        match="OPEX",
    ):
        (
            OpexNewRowAmountService()
            .apply(
                draft,
                monthly_values=(
                    zero_months()
                ),
            )
        )
