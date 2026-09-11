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
from app.config.capex_schema import (
    CAPEX_ML_MONTH_COLUMNS,
    CAPEX_ML_TOTAL_COLUMN,
    CAPEX_USD_MONTH_COLUMNS,
    CAPEX_USD_TOTAL_COLUMN,
)
from app.services.capex_new_row_amount_service import (
    CapexNewRowAmountError,
    CapexNewRowAmountService,
)
from app.services.new_budget_row_service import (
    NewBudgetRowService,
)


pytestmark = pytest.mark.unit


NOW = datetime(
    2026,
    9,
    11,
    20,
    0,
    tzinfo=timezone.utc,
)


def make_draft(
    *,
    year=2027,
    quantity=1,
):
    return (
        NewBudgetRowService(
            CAPEX_MODULE_CONFIG,
            row_id_factory=(
                lambda:
                    "capex-new-test"
            ),
        )
        .create_draft(
            {
                "anio":
                    year,
                "cantidad":
                    quantity,
                "pais":
                    "PER",
                "responsable":
                    "RESPONSABLE TEST",
                "presupuestador":
                    "PRESUPUESTADOR TEST",
                "nombre_inversion":
                    "PROYECTO TEST",
                "codigo_cebe":
                    "001234",
                "codigo_ceco":
                    "009876",
            },
            actor="tester",
            timestamp=NOW,
        )
    )


def zero_family(
    columns,
):
    return {
        column:
            "0"
        for column in columns
    }


def test_applies_both_capex_amount_families():
    ml = zero_family(
        CAPEX_ML_MONTH_COLUMNS
    )

    usd = zero_family(
        CAPEX_USD_MONTH_COLUMNS
    )

    ml[
        CAPEX_ML_MONTH_COLUMNS[0]
    ] = "100.123456789"

    ml[
        CAPEX_ML_MONTH_COLUMNS[1]
    ] = "200.000000001"

    usd[
        CAPEX_USD_MONTH_COLUMNS[0]
    ] = "30.50"

    usd[
        CAPEX_USD_MONTH_COLUMNS[1]
    ] = "70.25"

    result = (
        CapexNewRowAmountService()
        .apply(
            make_draft(),
            ml_values=ml,
            usd_values=usd,
        )
    )

    assert (
        result.row[
            CAPEX_ML_MONTH_COLUMNS[0]
        ]
        == Decimal(
            "100.123456789"
        )
    )

    assert (
        result.row[
            CAPEX_ML_TOTAL_COLUMN
        ]
        == Decimal(
            "300.123456790"
        )
    )

    assert (
        result.row[
            CAPEX_USD_TOTAL_COLUMN
        ]
        == Decimal(
            "100.750000000"
        )
    )


def test_blank_month_is_zero():
    ml = zero_family(
        CAPEX_ML_MONTH_COLUMNS
    )

    usd = zero_family(
        CAPEX_USD_MONTH_COLUMNS
    )

    ml[
        CAPEX_ML_MONTH_COLUMNS[0]
    ] = ""

    result = (
        CapexNewRowAmountService()
        .apply(
            make_draft(),
            ml_values=ml,
            usd_values=usd,
        )
    )

    assert (
        result.row[
            CAPEX_ML_MONTH_COLUMNS[0]
        ]
        == Decimal(
            "0.000000000"
        )
    )


def test_negative_amount_is_rejected():
    ml = zero_family(
        CAPEX_ML_MONTH_COLUMNS
    )

    usd = zero_family(
        CAPEX_USD_MONTH_COLUMNS
    )

    usd[
        CAPEX_USD_MONTH_COLUMNS[0]
    ] = "-1"

    with pytest.raises(
        CapexNewRowAmountError,
        match="negativo",
    ):
        (
            CapexNewRowAmountService()
            .apply(
                make_draft(),
                ml_values=ml,
                usd_values=usd,
            )
        )


def test_missing_month_is_rejected():
    ml = zero_family(
        CAPEX_ML_MONTH_COLUMNS
    )

    usd = zero_family(
        CAPEX_USD_MONTH_COLUMNS
    )

    del ml[
        CAPEX_ML_MONTH_COLUMNS[-1]
    ]

    with pytest.raises(
        CapexNewRowAmountError,
        match="Faltan meses ML",
    ):
        (
            CapexNewRowAmountService()
            .apply(
                make_draft(),
                ml_values=ml,
                usd_values=usd,
            )
        )


def test_wrong_year_is_rejected():
    with pytest.raises(
        CapexNewRowAmountError,
        match="2027",
    ):
        (
            CapexNewRowAmountService()
            .apply(
                make_draft(
                    year=2026
                ),
                ml_values=(
                    zero_family(
                        CAPEX_ML_MONTH_COLUMNS
                    )
                ),
                usd_values=(
                    zero_family(
                        CAPEX_USD_MONTH_COLUMNS
                    )
                ),
            )
        )


def test_negative_quantity_is_rejected():
    with pytest.raises(
        CapexNewRowAmountError,
        match="negativa",
    ):
        (
            CapexNewRowAmountService()
            .apply(
                make_draft(
                    quantity=-1
                ),
                ml_values=(
                    zero_family(
                        CAPEX_ML_MONTH_COLUMNS
                    )
                ),
                usd_values=(
                    zero_family(
                        CAPEX_USD_MONTH_COLUMNS
                    )
                ),
            )
        )


def test_preserves_codes_and_technical_metadata():
    result = (
        CapexNewRowAmountService()
        .apply(
            make_draft(),
            ml_values=(
                zero_family(
                    CAPEX_ML_MONTH_COLUMNS
                )
            ),
            usd_values=(
                zero_family(
                    CAPEX_USD_MONTH_COLUMNS
                )
            ),
        )
    )

    assert (
        result.row["codigo_cebe"]
        == "001234"
    )

    assert (
        result.row["codigo_ceco"]
        == "009876"
    )

    assert (
        result.row["row_id"]
        == "capex-new-test"
    )

    assert (
        result.row["version"]
        == 1
    )

    assert (
        result.row["habilitado"]
        is True
    )

    assert (
        result.row["created_at"]
        == NOW
    )

    assert (
        result.row["created_by"]
        == "tester"
    )


def test_opex_draft_is_rejected():
    draft = (
        NewBudgetRowService(
            OPEX_MODULE_CONFIG,
            row_id_factory=(
                lambda:
                    "opex-test"
            ),
        )
        .create_draft(
            {
                "pais":
                    "PER",
            },
            actor="tester",
            timestamp=NOW,
        )
    )

    with pytest.raises(
        CapexNewRowAmountError,
        match="CAPEX",
    ):
        (
            CapexNewRowAmountService()
            .apply(
                draft,
                ml_values=(
                    zero_family(
                        CAPEX_ML_MONTH_COLUMNS
                    )
                ),
                usd_values=(
                    zero_family(
                        CAPEX_USD_MONTH_COLUMNS
                    )
                ),
            )
        )
