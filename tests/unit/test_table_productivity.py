from decimal import Decimal

import pytest

from PySide6.QtCore import (
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
from app.ui.table_productivity import (
    TABLE_SHORTCUT_SEQUENCES,
)


pytestmark = pytest.mark.unit


class FakeConfig:
    amount_columns = (
        "enero_usd",
        "anio_usd",
    )

    month_columns = (
        "enero_usd",
    )

    annual_column = (
        "anio_usd"
    )

    editable_columns = (
        "enero_usd",
        "anio_usd",
    )

    insert_column_types = ()


class FakeWorkspace:
    module_config = FakeConfig()

    def __init__(
        self,
        row,
    ):
        self._row = dict(
            row
        )

    def get_original_row(
        self,
        row_id,
    ):
        return dict(
            self._row
        )

    def is_new_row(
        self,
        row_id,
    ):
        return False


def make_presupuesto_model():
    row = {
        SESSION_ROW_ID: 1,
        "habilitado": True,
        "enero_usd":
            Decimal("10.00"),
        "anio_usd":
            Decimal("120.00"),
    }

    model = PresupuestoTableModel(
        FakeWorkspace(
            row
        )
    )

    model.set_page(
        PageResult(
            rows=(row,),
            columns=(
                "enero_usd",
                "anio_usd",
            ),
            total_rows=1,
            page_index=0,
            page_size=250,
        )
    )

    return model


def test_presupuesto_annual_total_is_emphasized():
    model = (
        make_presupuesto_model()
    )

    annual = model.index(
        0,
        1,
    )

    assert (
        model.data(
            annual,
            Qt.ItemDataRole.BackgroundRole,
        )
        == model.ANNUAL_BACKGROUND
    )

    assert (
        model.data(
            annual,
            Qt.ItemDataRole.FontRole,
        )
        .bold()
    )


def test_presupuesto_month_keeps_regular_amount_style():
    model = (
        make_presupuesto_model()
    )

    month = model.index(
        0,
        0,
    )

    assert (
        model.data(
            month,
            Qt.ItemDataRole.BackgroundRole,
        )
        == model.USD_BACKGROUND
    )


def test_group_annual_total_is_emphasized():
    model = ResultTableModel(
        amount_columns=(
            "enero_usd",
            "anio_usd",
        ),
        annual_columns=(
            "anio_usd",
        ),
    )

    model.set_data(
        (
            {
                "enero_usd":
                    Decimal("10"),
                "anio_usd":
                    Decimal("120"),
            },
        ),
        (
            "enero_usd",
            "anio_usd",
        ),
    )

    annual = model.index(
        0,
        1,
    )

    assert (
        model.data(
            annual,
            Qt.ItemDataRole.BackgroundRole,
        )
        == model.ANNUAL_BACKGROUND
    )

    assert (
        model.data(
            annual,
            Qt.ItemDataRole.FontRole,
        )
        .bold()
    )


def test_table_shortcut_contract():
    assert (
        TABLE_SHORTCUT_SEQUENCES
        == (
            "Ctrl+F",
            "Ctrl+R",
            "Ctrl+Z",
            "Esc",
        )
    )
