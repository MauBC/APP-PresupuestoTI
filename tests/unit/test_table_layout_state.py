import pytest

from PySide6.QtCore import (
    Qt,
)

from app.ui.table_productivity import (
    capture_table_layout,
    merge_column_widths,
    restore_table_layout,
)


pytestmark = pytest.mark.unit


class FakeHeader:
    def __init__(
        self,
        section=0,
        order=(
            Qt.SortOrder
            .AscendingOrder
        ),
    ):
        self.section = section
        self.order = order

    def sortIndicatorSection(
        self,
    ):
        return self.section

    def sortIndicatorOrder(
        self,
    ):
        return self.order


class FakeTable:
    def __init__(
        self,
        widths,
        *,
        hidden=(),
        sort_section=0,
        sort_order=(
            Qt.SortOrder
            .AscendingOrder
        ),
    ):
        self.widths = list(
            widths
        )

        self.hidden = set(
            hidden
        )

        self.header = FakeHeader(
            sort_section,
            sort_order,
        )

        self.sorted = None

    def columnWidth(
        self,
        index,
    ):
        return self.widths[
            index
        ]

    def setColumnWidth(
        self,
        index,
        width,
    ):
        self.widths[
            index
        ] = width

    def isColumnHidden(
        self,
        index,
    ):
        return (
            index in self.hidden
        )

    def horizontalHeader(
        self,
    ):
        return self.header

    def sortByColumn(
        self,
        index,
        order,
    ):
        self.sorted = (
            index,
            order,
        )


def test_capture_uses_column_names():
    table = FakeTable(
        (
            120,
            210,
            160,
        ),
        sort_section=1,
        sort_order=(
            Qt.SortOrder
            .DescendingOrder
        ),
    )

    widths, column, order = (
        capture_table_layout(
            table=table,
            columns=(
                "pais",
                "presupuestador",
                "anio_usd",
            ),
        )
    )

    assert widths == (
        ("pais", 120),
        ("presupuestador", 210),
        ("anio_usd", 160),
    )

    assert (
        column
        == "presupuestador"
    )

    assert order == "desc"


def test_hidden_columns_do_not_destroy_widths():
    table = FakeTable(
        (
            120,
            0,
            160,
        ),
        hidden=(1,),
    )

    widths, _, _ = (
        capture_table_layout(
            table=table,
            columns=(
                "pais",
                "enero_usd",
                "anio_usd",
            ),
        )
    )

    assert widths == (
        ("pais", 120),
        ("anio_usd", 160),
    )


def test_merge_keeps_hidden_previous_width():
    result = merge_column_widths(
        (
            ("enero_usd", 135),
            ("anio_usd", 150),
        ),
        (
            ("anio_usd", 190),
        ),
    )

    assert dict(result) == {
        "enero_usd": 135,
        "anio_usd": 190,
    }


def test_restore_matches_columns_by_name():
    table = FakeTable(
        (
            100,
            100,
            100,
        )
    )

    restore_table_layout(
        table=table,
        columns=(
            "pais",
            "presupuestador",
            "anio_usd",
        ),
        column_widths=(
            ("anio_usd", 220),
            ("pais", 140),
        ),
        sort_column="anio_usd",
        sort_order="desc",
    )

    assert table.widths == [
        140,
        100,
        220,
    ]

    assert table.sorted == (
        2,
        Qt.SortOrder
        .DescendingOrder,
    )


def test_missing_sort_column_is_ignored():
    table = FakeTable(
        (
            100,
            100,
        )
    )

    restore_table_layout(
        table=table,
        columns=(
            "pais",
            "anio_usd",
        ),
        sort_column=(
            "no_existe"
        ),
        sort_order="desc",
    )

    assert table.sorted is None
