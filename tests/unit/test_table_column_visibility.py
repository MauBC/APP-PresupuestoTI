import pytest

from app.ui.table_column_visibility import (
    apply_month_column_visibility,
)


pytestmark = pytest.mark.unit


class FakeTable:
    def __init__(self):
        self.hidden = {}

    def setColumnHidden(
        self,
        index,
        hidden,
    ):
        self.hidden[index] = bool(
            hidden
        )


def test_opex_months_hidden_but_annual_total_visible():
    table = FakeTable()

    columns = (
        "pais",
        "proveedor",
        "enero_usd",
        "febrero_usd",
        "anio_usd",
    )

    matched = (
        apply_month_column_visibility(
            table=table,
            columns=columns,
            month_columns=(
                "enero_usd",
                "febrero_usd",
            ),
            months_visible=False,
        )
    )

    assert matched == 2
    assert table.hidden[0] is False
    assert table.hidden[1] is False
    assert table.hidden[2] is True
    assert table.hidden[3] is True
    assert table.hidden[4] is False


def test_capex_hides_ml_and_usd_months_but_keeps_totals():
    table = FakeTable()

    columns = (
        "nombre_inversion",
        "01_ml",
        "02_ml",
        "total_ml",
        "01_usd",
        "02_usd",
        "total_usd",
    )

    apply_month_column_visibility(
        table=table,
        columns=columns,
        month_columns=(
            "01_ml",
            "02_ml",
            "01_usd",
            "02_usd",
        ),
        months_visible=False,
    )

    assert table.hidden[0] is False
    assert table.hidden[1] is True
    assert table.hidden[2] is True
    assert table.hidden[3] is False
    assert table.hidden[4] is True
    assert table.hidden[5] is True
    assert table.hidden[6] is False


def test_show_months_restores_same_columns():
    table = FakeTable()

    columns = (
        "pais",
        "enero_usd",
        "febrero_usd",
        "anio_usd",
    )

    apply_month_column_visibility(
        table=table,
        columns=columns,
        month_columns=(
            "enero_usd",
            "febrero_usd",
        ),
        months_visible=False,
    )

    apply_month_column_visibility(
        table=table,
        columns=columns,
        month_columns=(
            "enero_usd",
            "febrero_usd",
        ),
        months_visible=True,
    )

    assert all(
        hidden is False
        for hidden in table.hidden.values()
    )


def test_no_month_columns_is_safe():
    table = FakeTable()

    matched = (
        apply_month_column_visibility(
            table=table,
            columns=(
                "pais",
                "anio_usd",
            ),
            month_columns=(),
            months_visible=False,
        )
    )

    assert matched == 0
    assert table.hidden == {
        0: False,
        1: False,
    }
