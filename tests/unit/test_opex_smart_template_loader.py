from decimal import Decimal

import pandas as pd
import pytest

from app.services.opex_smart_template_loader import (
    OpexSmartTemplateError,
    OpexSmartTemplateLoader,
)


pytestmark = pytest.mark.unit


def write_book(
    path,
    *,
    distribution_headers,
    distributions,
    tipo="MENSUAL",
    monto=30000,
):
    rows = [
        [
            "Nombre del Gasto",
            "GASTO TEST",
            None,
        ],
        [
            "Proveedor",
            "PROVEEDOR TEST",
            None,
        ],
        [
            "Moneda de Facturación",
            "USD",
            None,
        ],
        [
            "Número de cuenta",
            635610007,
            None,
        ],
        [
            "TIPO",
            tipo,
            None,
        ],
        [
            "MONTO",
            monto,
            None,
        ],
        list(
            distribution_headers
        ),
        *[
            list(
                row
            )
            for row
            in distributions
        ],
    ]

    dataframe = pd.DataFrame(
        rows
    )

    dataframe.to_excel(
        path,
        index=False,
        header=False,
    )


def test_reads_percentage_and_amount(
    tmp_path,
):
    path = (
        tmp_path
        / "both.xlsx"
    )

    write_book(
        path,
        distribution_headers=(
            "CECOS",
            "PORCENTAJE",
            "IMPORTE",
        ),
        distributions=(
            (
                "291ACC9904",
                0.40,
                12000,
            ),
            (
                "264000T2K4",
                0.60,
                18000,
            ),
        ),
    )

    result = (
        OpexSmartTemplateLoader()
        .load(
            path
        )
    )

    budget = result.budgets[0]

    assert (
        budget.distribution_mode
        == "PORCENTAJE+IMPORTE"
    )

    assert (
        budget.total_percentage
        == Decimal("1.0")
    )

    assert (
        budget
        .total_distribution_amount
        == Decimal("30000")
    )

    assert budget.ceco_count == 2


def test_reads_amount_only(
    tmp_path,
):
    path = (
        tmp_path
        / "amount.xlsx"
    )

    write_book(
        path,
        distribution_headers=(
            "CECOS",
            "IMPORTE",
        ),
        distributions=(
            (
                "51BA000X04",
                100,
            ),
            (
                "51BX000004",
                200,
            ),
        ),
    )

    budget = (
        OpexSmartTemplateLoader()
        .load(
            path
        )
        .budgets[0]
    )

    assert (
        budget.distribution_mode
        == "IMPORTE"
    )

    assert (
        budget.total_percentage
        is None
    )

    assert (
        budget
        .total_distribution_amount
        == Decimal("300")
    )


def test_reads_percentage_only(
    tmp_path,
):
    path = (
        tmp_path
        / "percentage.xlsx"
    )

    write_book(
        path,
        distribution_headers=(
            "CECOS",
            "PORCENTAJE",
        ),
        distributions=(
            (
                "291ACC9904",
                "40%",
            ),
            (
                "264000T2K4",
                "60%",
            ),
        ),
    )

    budget = (
        OpexSmartTemplateLoader()
        .load(
            path
        )
        .budgets[0]
    )

    assert (
        budget.distribution_mode
        == "PORCENTAJE"
    )

    assert (
        budget.total_percentage
        == Decimal("1.0")
    )


def test_account_is_preserved_as_string(
    tmp_path,
):
    path = (
        tmp_path
        / "account.xlsx"
    )

    write_book(
        path,
        distribution_headers=(
            "CECOS",
            "IMPORTE",
        ),
        distributions=(
            (
                "51BA000X04",
                100,
            ),
        ),
    )

    budget = (
        OpexSmartTemplateLoader()
        .load(
            path
        )
        .budgets[0]
    )

    assert (
        budget.numero_cuenta
        == "635610007"
    )


def test_duplicate_ceco_is_rejected(
    tmp_path,
):
    path = (
        tmp_path
        / "duplicate.xlsx"
    )

    write_book(
        path,
        distribution_headers=(
            "CECOS",
            "IMPORTE",
        ),
        distributions=(
            (
                "291ACC9904",
                100,
            ),
            (
                "291ACC9904",
                200,
            ),
        ),
    )

    with pytest.raises(
        OpexSmartTemplateError,
        match="CECO repetido",
    ):
        (
            OpexSmartTemplateLoader()
            .load(
                path
            )
        )


def test_invalid_type_is_rejected(
    tmp_path,
):
    path = (
        tmp_path
        / "type.xlsx"
    )

    write_book(
        path,
        distribution_headers=(
            "CECOS",
            "IMPORTE",
        ),
        distributions=(
            (
                "291ACC9904",
                100,
            ),
        ),
        tipo="OTRO",
    )

    with pytest.raises(
        OpexSmartTemplateError,
        match="MENSUAL o ANUAL",
    ):
        (
            OpexSmartTemplateLoader()
            .load(
                path
            )
        )


def test_ceco_requires_distribution(
    tmp_path,
):
    path = (
        tmp_path
        / "empty_distribution.xlsx"
    )

    write_book(
        path,
        distribution_headers=(
            "CECOS",
            "PORCENTAJE",
            "IMPORTE",
        ),
        distributions=(
            (
                "291ACC9904",
                None,
                None,
            ),
        ),
    )

    with pytest.raises(
        OpexSmartTemplateError,
        match="PORCENTAJE ni IMPORTE",
    ):
        (
            OpexSmartTemplateLoader()
            .load(
                path
            )
        )


def test_percentage_above_100_is_rejected(
    tmp_path,
):
    path = (
        tmp_path
        / "bad_percentage.xlsx"
    )

    write_book(
        path,
        distribution_headers=(
            "CECOS",
            "PORCENTAJE",
        ),
        distributions=(
            (
                "291ACC9904",
                40,
            ),
        ),
    )

    with pytest.raises(
        OpexSmartTemplateError,
        match="entre 0% y 100%",
    ):
        (
            OpexSmartTemplateLoader()
            .load(
                path
            )
        )
