from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services.opex_fx_loader import (
    OpexFxLoadError,
    OpexFxLoader,
)


pytestmark = pytest.mark.unit


def write_book(
    path,
    rows,
):
    wb = Workbook()

    ws = wb.active
    ws.title = "TC"

    ws.append(
        (
            "Pais",
            "Moneda",
            "TC",
        )
    )

    for row in rows:
        ws.append(
            row
        )

    wb.save(
        path
    )


def test_loads_official_tc_contract(
    tmp_path,
):
    path = (
        tmp_path
        / "TC.xlsx"
    )

    write_book(
        path,
        (
            (
                "Perú",
                "PEN",
                3.4,
            ),
            (
                "Colombia",
                "COP",
                3300,
            ),
            (
                "Ecuador",
                "USD",
                1,
            ),
        ),
    )

    result = (
        OpexFxLoader()
        .load(
            path
        )
    )

    assert (
        result.currency_per_usd[
            "PEN"
        ]
        == Decimal("3.40")
    )

    assert (
        result.currency_per_usd[
            "COP"
        ]
        == Decimal("3300.00")
    )

    assert (
        result.local_currency_by_country[
            "PE"
        ]
        == "PEN"
    )

    assert (
        result.local_currency_by_country[
            "CO"
        ]
        == "COP"
    )


def test_tc_is_rounded_to_two_decimals(
    tmp_path,
):
    path = (
        tmp_path
        / "TC.xlsx"
    )

    write_book(
        path,
        (
            (
                "Guatemala",
                "GTQ",
                7.715,
            ),
            (
                "México",
                "MXN",
                17.475456858678942,
            ),
        ),
    )

    result = (
        OpexFxLoader()
        .load(
            path
        )
    )

    assert str(
        result.currency_per_usd[
            "GTQ"
        ]
    ) == "7.72"

    assert str(
        result.currency_per_usd[
            "MXN"
        ]
    ) == "17.48"


def test_usd_country_requires_tc_one(
    tmp_path,
):
    path = (
        tmp_path
        / "TC.xlsx"
    )

    write_book(
        path,
        (
            (
                "Nicaragua",
                "USD",
                36.62,
            ),
        ),
    )

    with pytest.raises(
        OpexFxLoadError,
        match="USD.*1.00",
    ):
        (
            OpexFxLoader()
            .load(
                path
            )
        )


def test_unknown_country_is_blocked(
    tmp_path,
):
    path = (
        tmp_path
        / "TC.xlsx"
    )

    write_book(
        path,
        (
            (
                "Atlantida",
                "ATL",
                10,
            ),
        ),
    )

    with pytest.raises(
        OpexFxLoadError,
        match="no reconocido",
    ):
        (
            OpexFxLoader()
            .load(
                path
            )
        )

def test_nicaragua_uses_nio_currency(
    tmp_path,
):
    path = (
        tmp_path
        / "TC.xlsx"
    )

    write_book(
        path,
        (
            (
                "Nicaragua",
                "NIO",
                36.62,
            ),
        ),
    )

    result = (
        OpexFxLoader()
        .load(
            path
        )
    )

    assert (
        result.local_currency_by_country[
            "NI"
        ]
        == "NIO"
    )

    assert (
        result.currency_per_usd[
            "NIO"
        ]
        == Decimal("36.62")
    )

