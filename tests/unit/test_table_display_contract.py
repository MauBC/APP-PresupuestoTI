from decimal import Decimal

import pytest

from PySide6.QtCore import (
    QSortFilterProxyModel,
    Qt,
)

from app.models.page_result import (
    PageResult,
)
from app.services.presupuesto_workspace import (
    SESSION_ROW_ID,
)
from app.ui.models.presupuesto_table_model import (
    PresupuestoTableModel,
)
from app.ui.models.result_table_model import (
    ResultTableModel,
)


pytestmark = pytest.mark.unit


class FakeModuleConfig:
    amount_columns = (
        "enero_usd",
        "anio_usd",
    )

    month_columns = (
        "enero_usd",
    )

    annual_column = "anio_usd"


class FakeWorkspace:
    module_config = FakeModuleConfig()

    def __init__(
        self,
        rows,
    ):
        self._rows = {
            row[SESSION_ROW_ID]:
                dict(row)
            for row in rows
        }

    def get_original_row(
        self,
        row_id,
    ):
        return dict(
            self._rows[row_id]
        )

    def is_new_row(
        self,
        row_id,
    ):
        return False


def test_presupuesto_row_number_uses_page_offset():
    rows = (
        {
            SESSION_ROW_ID: 7,
            "enero_usd":
                Decimal("125.50"),
            "anio_usd":
                Decimal("125.50"),
        },
    )

    page = PageResult(
        rows=rows,
        columns=(
            "enero_usd",
            "anio_usd",
        ),
        total_rows=501,
        page_index=2,
        page_size=250,
    )

    model = PresupuestoTableModel(
        FakeWorkspace(rows)
    )

    model.set_page(
        page
    )

    assert (
        model.headerData(
            0,
            Qt.Orientation.Vertical,
            Qt.ItemDataRole.DisplayRole,
        )
        == 501
    )


def test_presupuesto_money_sort_role_is_numeric():
    rows = (
        {
            SESSION_ROW_ID: 1,
            "enero_usd":
                Decimal("100.00"),
            "anio_usd":
                Decimal("100.00"),
        },
        {
            SESSION_ROW_ID: 2,
            "enero_usd":
                Decimal("9.00"),
            "anio_usd":
                Decimal("9.00"),
        },
    )

    page = PageResult(
        rows=rows,
        columns=("enero_usd",),
        total_rows=2,
        page_index=0,
        page_size=250,
    )

    model = PresupuestoTableModel(
        FakeWorkspace(rows)
    )

    model.set_page(
        page
    )

    proxy = QSortFilterProxyModel()

    proxy.setSourceModel(
        model
    )

    proxy.setSortRole(
        Qt.ItemDataRole.UserRole
    )

    proxy.sort(
        0,
        Qt.SortOrder.AscendingOrder,
    )

    assert (
        proxy.data(
            proxy.index(0, 0),
            Qt.ItemDataRole.UserRole,
        )
        == 9.0
    )

    assert (
        proxy.data(
            proxy.index(1, 0),
            Qt.ItemDataRole.UserRole,
        )
        == 100.0
    )


def test_group_money_sort_role_is_numeric():
    model = ResultTableModel(
        amount_columns=(
            "total_usd",
        )
    )

    model.set_data(
        (
            {
                "total_usd":
                    Decimal("1500.00")
            },
            {
                "total_usd":
                    Decimal("25.00")
            },
        ),
        ("total_usd",),
    )

    proxy = QSortFilterProxyModel()

    proxy.setSourceModel(
        model
    )

    proxy.setSortRole(
        Qt.ItemDataRole.UserRole
    )

    proxy.sort(
        0,
        Qt.SortOrder.AscendingOrder,
    )

    assert (
        proxy.data(
            proxy.index(0, 0),
            Qt.ItemDataRole.UserRole,
        )
        == 25.0
    )

    assert (
        proxy.data(
            proxy.index(1, 0),
            Qt.ItemDataRole.UserRole,
        )
        == 1500.0
    )
