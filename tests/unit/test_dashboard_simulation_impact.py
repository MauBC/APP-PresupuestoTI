from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.ui.pages.dashboard_page import (
    build_dashboard_simulation_impact,
)


pytestmark = pytest.mark.unit


def make_summary(
    *,
    original,
    simulated,
    difference,
    variation,
    pending_rows,
    pending_fields,
):
    return SimpleNamespace(
        original_total=Decimal(original),
        simulated_total=Decimal(simulated),
        difference=Decimal(difference),
        variation_percent=(
            None
            if variation is None
            else Decimal(variation)
        ),
        pending_rows=pending_rows,
        pending_fields=pending_fields,
    )


def test_simulation_impact_increase_is_unfavorable():
    result = build_dashboard_simulation_impact(
        make_summary(
            original="1000",
            simulated="1250",
            difference="250",
            variation="25",
            pending_rows=2,
            pending_fields=4,
        )
    )

    assert result["state"] == "increase"
    assert result["has_changes"] is True
    assert result["difference_text"] == "+US$ 250.00"
    assert result["variation_text"] == "+25.00%"
    assert result["pending_text"] == "2 filas / 4 campos"


def test_simulation_impact_decrease_is_favorable():
    result = build_dashboard_simulation_impact(
        make_summary(
            original="1000",
            simulated="800",
            difference="-200",
            variation="-20",
            pending_rows=1,
            pending_fields=1,
        )
    )

    assert result["state"] == "decrease"
    assert result["difference_text"] == "US$ -200.00"
    assert result["variation_text"] == "-20.00%"


def test_simulation_impact_without_changes_is_neutral():
    result = build_dashboard_simulation_impact(
        make_summary(
            original="1000",
            simulated="1000",
            difference="0",
            variation="0",
            pending_rows=0,
            pending_fields=0,
        )
    )

    assert result["state"] == "neutral"
    assert result["has_changes"] is False
    assert result["pending_text"] == "0 filas / 0 campos"

    assert (
        result["summary_text"]
        == "Sin cambios pendientes en el Workspace."
    )


def test_simulation_impact_supports_undefined_variation():
    result = build_dashboard_simulation_impact(
        make_summary(
            original="0",
            simulated="100",
            difference="100",
            variation=None,
            pending_rows=1,
            pending_fields=12,
        )
    )

    assert result["variation_text"] == "N/D"
    assert result["state"] == "increase"
