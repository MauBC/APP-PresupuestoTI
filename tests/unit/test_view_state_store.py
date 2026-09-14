import pytest

from app.config.budget_module_config import (
    BudgetModule,
)
from app.ui.view_state_store import (
    AggregationViewState,
    PresupuestoViewState,
    UiViewStateStore,
)


pytestmark = pytest.mark.unit


class FakeSettings:
    def __init__(
        self,
        values=None,
    ):
        self.values = dict(
            values
            or {}
        )

        self.synced = False

    def value(
        self,
        key,
        default=None,
    ):
        return self.values.get(
            key,
            default,
        )

    def setValue(
        self,
        key,
        value,
    ):
        self.values[
            key
        ] = value

    def sync(
        self,
    ):
        self.synced = True


def test_default_state_is_safe():
    store = UiViewStateStore(
        FakeSettings()
    )

    assert (
        store.active_module()
        == BudgetModule.OPEX
    )

    assert not (
        store.sidebar_expanded()
    )

    assert (
        store.last_page(
            BudgetModule.OPEX
        )
        == 0
    )

    assert (
        store.presupuesto_state(
            BudgetModule.OPEX
        )
        == PresupuestoViewState()
    )

    assert (
        store.aggregation_state(
            BudgetModule.OPEX
        )
        == AggregationViewState()
    )


def test_global_state_round_trip():
    backend = FakeSettings()

    store = UiViewStateStore(
        backend
    )

    store.set_sidebar_expanded(
        True
    )

    store.set_active_module(
        BudgetModule.CAPEX
    )

    store.set_last_page(
        BudgetModule.CAPEX,
        2,
    )

    assert store.sidebar_expanded()

    assert (
        store.active_module()
        == BudgetModule.CAPEX
    )

    assert (
        store.last_page(
            BudgetModule.CAPEX
        )
        == 2
    )


def test_presupuesto_state_is_independent_by_module():
    backend = FakeSettings()

    store = UiViewStateStore(
        backend
    )

    store.set_presupuesto_state(
        BudgetModule.OPEX,
        PresupuestoViewState(
            search="MICROSOFT",
            page_size=500,
            enabled_filter="enabled",
            months_visible=False,
            page_index=3,
        ),
    )

    store.set_presupuesto_state(
        BudgetModule.CAPEX,
        PresupuestoViewState(
            search="TRANSFORMACION",
            page_size=100,
            enabled_filter="all",
            months_visible=True,
            page_index=1,
        ),
    )

    opex = (
        store.presupuesto_state(
            BudgetModule.OPEX
        )
    )

    capex = (
        store.presupuesto_state(
            BudgetModule.CAPEX
        )
    )

    assert opex.search == "MICROSOFT"
    assert opex.page_size == 500
    assert not opex.months_visible

    assert (
        capex.search
        == "TRANSFORMACION"
    )

    assert capex.page_size == 100
    assert capex.enabled_filter == "all"
    assert capex.months_visible


def test_aggregation_groups_round_trip():
    backend = FakeSettings()

    store = UiViewStateStore(
        backend
    )

    expected = (
        AggregationViewState(
            search="PERU",
            months_visible=True,
            groups=(
                "pais",
                "presupuestador",
                None,
                None,
                None,
            ),
        )
    )

    store.set_aggregation_state(
        BudgetModule.OPEX,
        expected,
    )

    assert (
        store.aggregation_state(
            BudgetModule.OPEX
        )
        == expected
    )


def test_invalid_values_fall_back_to_defaults():
    backend = FakeSettings(
        {
            "global/active_module":
                "OTRO",
            (
                "modules/OPEX/"
                "last_page"
            ):
                99,
            (
                "modules/OPEX/"
                "presupuesto/"
                "page_size"
            ):
                999,
            (
                "modules/OPEX/"
                "presupuesto/"
                "enabled_filter"
            ):
                "otro",
            (
                "modules/OPEX/"
                "presupuesto/"
                "page_index"
            ):
                -5,
        }
    )

    store = UiViewStateStore(
        backend
    )

    state = (
        store.presupuesto_state(
            BudgetModule.OPEX
        )
    )

    assert (
        store.active_module()
        == BudgetModule.OPEX
    )

    assert (
        store.last_page(
            BudgetModule.OPEX
        )
        == 0
    )

    assert state.page_size == 250

    assert (
        state.enabled_filter
        == "enabled"
    )

    assert state.page_index == 0
