from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.services.new_budget_row_service import (
    NewBudgetRowError,
    NewBudgetRowService,
)


pytestmark = pytest.mark.unit

PERCENT_CENT = Decimal("0.01")
HUNDRED = Decimal("100.00")


def equal_percentages(
    config,
):
    columns = tuple(
        config.month_columns
    )

    base = (
        HUNDRED
        / Decimal(
            len(columns)
        )
    ).quantize(
        PERCENT_CENT,
        rounding=ROUND_HALF_UP,
    )

    result = {
        column: base
        for column in columns
    }

    result[
        columns[-1]
    ] += (
        HUNDRED
        - sum(
            result.values(),
            Decimal("0.00"),
        )
    )

    return result


def capex_dimensions():
    return {
        "pais": "PER",
        "presupuestador":
            "TEST C2.2",
        "responsable":
            "RESPONSABLE TEST",
        "anio": 2027,
        "cantidad": 1,
        "nombre_inversion":
            "PROYECTO C2.2",
    }


def opex_dimensions():
    return {
        "pais": "PER",
        "presupuestador":
            "TEST C2.2",
        "nombre_gasto":
            "GASTO C2.2",
    }


@pytest.mark.parametrize(
    (
        "config",
        "dimensions",
        "row_id",
    ),
    (
        (
            CAPEX_MODULE_CONFIG,
            capex_dimensions(),
            "capex-c2-2",
        ),
        (
            OPEX_MODULE_CONFIG,
            opex_dimensions(),
            "opex-c2-2",
        ),
    ),
)
def test_new_row_supports_monthly_distribution(
    config,
    dimensions,
    row_id,
):
    service = NewBudgetRowService(
        config,
        row_id_factory=(
            lambda: row_id
        ),
    )

    draft = service.create_draft(
        dimensions,
        actor="tester",
    )

    original = dict(
        draft.row
    )

    distributed = (
        service
        .with_monthly_distribution(
            draft,
            percentages=(
                equal_percentages(
                    config
                )
            ),
            annual_total=(
                Decimal("120000.00")
            ),
        )
    )

    assert (
        distributed.module
        == config.module.value
    )

    assert (
        distributed.row["row_id"]
        == row_id
    )

    assert (
        distributed.row[
            config.annual_column
        ]
        == Decimal("120000.00")
    )

    assert (
        sum(
            (
                distributed.row[column]
                for column
                in config.month_columns
            ),
            Decimal("0.00"),
        )
        == Decimal("120000.00")
    )

    for column, value in (
        dimensions.items()
    ):
        assert (
            distributed.row[column]
            == value
        )

    # El draft original no se muta.
    assert draft.row == original


def test_distribution_keeps_cent_residual_exact():
    config = CAPEX_MODULE_CONFIG

    service = NewBudgetRowService(
        config,
        row_id_factory=(
            lambda:
                "capex-residual"
        ),
    )

    draft = service.create_draft(
        capex_dimensions(),
        actor="tester",
    )

    distributed = (
        service
        .with_monthly_distribution(
            draft,
            percentages=(
                equal_percentages(
                    config
                )
            ),
            annual_total=(
                Decimal("100.00")
            ),
        )
    )

    assert (
        sum(
            (
                distributed.row[column]
                for column
                in config.month_columns
            ),
            Decimal("0.00"),
        )
        == Decimal("100.00")
    )

    assert (
        distributed.row[
            config.annual_column
        ]
        == Decimal("100.00")
    )


def test_invalid_percentage_distribution_is_rejected():
    config = CAPEX_MODULE_CONFIG

    service = NewBudgetRowService(
        config
    )

    draft = service.create_draft(
        capex_dimensions(),
        actor="tester",
    )

    percentages = {
        column:
            Decimal("0.00")
        for column
        in config.month_columns
    }

    percentages[
        config.month_columns[0]
    ] = Decimal("99.00")

    with pytest.raises(
        NewBudgetRowError,
        match="Falta",
    ):
        service.with_monthly_distribution(
            draft,
            percentages=percentages,
            annual_total=(
                Decimal("100.00")
            ),
        )


def test_negative_annual_amount_is_rejected():
    config = CAPEX_MODULE_CONFIG

    service = NewBudgetRowService(
        config
    )

    draft = service.create_draft(
        capex_dimensions(),
        actor="tester",
    )

    with pytest.raises(
        NewBudgetRowError,
        match="negativo",
    ):
        service.with_monthly_distribution(
            draft,
            percentages=(
                equal_percentages(
                    config
                )
            ),
            annual_total=(
                Decimal("-1.00")
            ),
        )


def test_draft_from_other_module_is_rejected():
    opex_service = (
        NewBudgetRowService(
            OPEX_MODULE_CONFIG
        )
    )

    capex_service = (
        NewBudgetRowService(
            CAPEX_MODULE_CONFIG
        )
    )

    draft = (
        opex_service
        .create_draft(
            opex_dimensions(),
            actor="tester",
        )
    )

    with pytest.raises(
        NewBudgetRowError,
        match="modulo diferente",
    ):
        (
            capex_service
            .with_monthly_distribution(
                draft,
                percentages=(
                    equal_percentages(
                        CAPEX_MODULE_CONFIG
                    )
                ),
                annual_total=(
                    Decimal("100.00")
                ),
            )
        )
