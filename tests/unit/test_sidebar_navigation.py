import pytest

from app.ui.sidebar_navigation import (
    NAVIGATION_ITEMS,
    navigation_context_text,
    sidebar_width,
)


pytestmark = pytest.mark.unit


def test_navigation_items_have_expected_order():
    assert tuple(
        item.label
        for item in NAVIGATION_ITEMS
    ) == (
        "Dashboard",
        "Presupuesto",
        "Agrupaciones",
        "Historial",
    )

    assert tuple(
        item.page_index
        for item in NAVIGATION_ITEMS
    ) == (
        0,
        1,
        2,
        3,
    )


def test_navigation_page_indexes_are_unique():
    indexes = tuple(
        item.page_index
        for item in NAVIGATION_ITEMS
    )

    assert len(
        indexes
    ) == len(
        set(indexes)
    )


def test_navigation_context_combines_module_and_page():
    assert (
        navigation_context_text(
            "OPEX",
            1,
        )
        == "OPEX  /  Presupuesto"
    )

    assert (
        navigation_context_text(
            "CAPEX",
            2,
        )
        == "CAPEX  /  Agrupaciones"
    )


def test_sidebar_width_switches_between_modes():
    assert (
        sidebar_width(
            expanded=False,
            expanded_width=240,
            compact_width=84,
        )
        == 84
    )

    assert (
        sidebar_width(
            expanded=True,
            expanded_width=240,
            compact_width=84,
        )
        == 240
    )
