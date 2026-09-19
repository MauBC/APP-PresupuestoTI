import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.ui.frozen_columns import (
    FrozenColumnsController,
    resolve_frozen_columns,
)
from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QTableView


pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("config", [OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG])
def test_frozen_overlay_covers_only_its_own_columns(qapp, config):
    columns = config.dimension_columns + config.amount_columns
    model = QStandardItemModel(2, len(columns))
    for column, name in enumerate(columns):
        model.setHorizontalHeaderItem(column, QStandardItem(name))
        model.setItem(0, column, QStandardItem("B"))
        model.setItem(1, column, QStandardItem("A"))
    proxy = QSortFilterProxyModel()
    proxy.setSourceModel(model)
    table = QTableView()
    table.setModel(proxy)
    table.resize(1100, 450)
    table.horizontalHeader().setDefaultSectionSize(100)
    controller = FrozenColumnsController(main_table=table, preferred_columns=config.frozen_context_columns)
    try:
        controller.sync(columns=columns)
        table.show()
        qapp.processEvents()
        preferred = [columns.index(name) for name in config.frozen_context_columns]
        header = table.horizontalHeader()
        expected = preferred + [i for i in range(len(columns)) if i not in preferred]
        assert [header.logicalIndex(i) for i in range(len(columns))] == expected
        for index in preferred:
            assert header.sectionPosition(index) == controller.view.horizontalHeader().sectionPosition(index)
            assert table.columnWidth(index) == controller.view.columnWidth(index)
        first_free = expected[len(preferred)]
        assert header.sectionPosition(first_free) == sum(table.columnWidth(i) for i in preferred)
        # Visual movement must not change logical column identities or sort routing.
        assert tuple(model.headerData(i, Qt.Orientation.Horizontal) for i in range(len(columns))) == columns
        table.setSortingEnabled(True)
        controller._sort_from_frozen_header(preferred[0])
        assert proxy.sortColumn() == preferred[0]
        table.setColumnWidth(preferred[0], 180)
        assert controller.view.columnWidth(preferred[0]) == 180
        controller.sync(columns=columns)
        assert [header.logicalIndex(i) for i in range(len(columns))] == expected
        proxy.setFilterFixedString("A")
        assert controller.view.model().rowCount() == table.model().rowCount() == 1
        table.selectRow(0)
        assert controller.view.selectionModel() is table.selectionModel()
    finally:
        table.close()


def test_resolve_frozen_columns_preserves_preference_order():
    result = resolve_frozen_columns(
        columns=(
            "pais",
            "presupuestador",
            "nombre_inversion",
            "anio_usd",
        ),
        preferred_columns=(
            "presupuestador",
            "pais",
            "nombre_inversion",
        ),
    )

    assert result == (
        "presupuestador",
        "pais",
        "nombre_inversion",
    )


def test_resolve_frozen_columns_ignores_missing_and_duplicates():
    result = resolve_frozen_columns(
        columns=(
            "pais",
            "nombre_gasto",
        ),
        preferred_columns=(
            "pais",
            "no_existe",
            "pais",
            "nombre_gasto",
        ),
    )

    assert result == (
        "pais",
        "nombre_gasto",
    )


def test_opex_frozen_context_contract():
    assert (
        OPEX_MODULE_CONFIG
        .frozen_context_columns
        == (
            "presupuestador",
            "pais",
            "nombre_gasto",
        )
    )

    assert set(
        OPEX_MODULE_CONFIG
        .frozen_context_columns
    ).issubset(
        OPEX_MODULE_CONFIG
        .dimension_columns
    )


def test_capex_frozen_context_contract():
    assert (
        CAPEX_MODULE_CONFIG
        .frozen_context_columns
        == (
            "presupuestador",
            "pais",
            "nombre_inversion",
        )
    )

    assert set(
        CAPEX_MODULE_CONFIG
        .frozen_context_columns
    ).issubset(
        CAPEX_MODULE_CONFIG
        .dimension_columns
    )
