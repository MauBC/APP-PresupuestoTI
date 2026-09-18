import pytest

from app.config.budget_insert_modes import (
    BudgetInsertMode,
    get_budget_insert_options,
)
from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)


pytestmark = pytest.mark.unit


def test_opex_has_four_insert_modes():
    options = (
        get_budget_insert_options(
            OPEX_MODULE_CONFIG
        )
    )

    assert tuple(
        option.mode
        for option in options
    ) == (
        BudgetInsertMode.MANUAL,
        BudgetInsertMode.ASSISTED,
        BudgetInsertMode.INTELLIGENT,
        BudgetInsertMode.TEMPLATE,
    )


def test_capex_has_two_insert_modes():
    options = (
        get_budget_insert_options(
            CAPEX_MODULE_CONFIG
        )
    )

    assert tuple(
        option.mode
        for option in options
    ) == (
        BudgetInsertMode.MANUAL,
        BudgetInsertMode.TEMPLATE,
    )


def test_manual_and_template_are_enabled():
    for config in (
        OPEX_MODULE_CONFIG,
        CAPEX_MODULE_CONFIG,
    ):
        options = (
            get_budget_insert_options(
                config
            )
        )

        enabled = {
            option.mode:
                option.enabled
            for option in options
        }

        assert (
            enabled[
                BudgetInsertMode.MANUAL
            ]
            is True
        )

        assert (
            enabled[
                BudgetInsertMode.TEMPLATE
            ]
            is True
        )


def test_assisted_is_visible_and_enabled_for_opex():
    options = (
        get_budget_insert_options(
            OPEX_MODULE_CONFIG
        )
    )

    assisted = next(
        option
        for option in options
        if (
            option.mode
            == BudgetInsertMode.ASSISTED
        )
    )

    assert assisted.title == "Alta asistida"
    assert assisted.enabled is True


def test_intelligent_template_keeps_existing_flow():
    options = (
        get_budget_insert_options(
            OPEX_MODULE_CONFIG
        )
    )

    intelligent = next(
        option
        for option in options
        if (
            option.mode
            == BudgetInsertMode.INTELLIGENT
        )
    )

    assert (
        intelligent.title
        == "Inteligente por plantilla"
    )

    assert intelligent.enabled is True


def test_capex_does_not_expose_opex_specific_modes():
    modes = {
        option.mode
        for option in (
            get_budget_insert_options(
                CAPEX_MODULE_CONFIG
            )
        )
    }

    assert (
        BudgetInsertMode.ASSISTED
        not in modes
    )

    assert (
        BudgetInsertMode.INTELLIGENT
        not in modes
    )
