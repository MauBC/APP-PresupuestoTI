import os
from types import SimpleNamespace

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.services.presupuesto_change_summary_service import (
    CHANGE_TYPE_DISABLED,
    CHANGE_TYPE_EDITED,
    ChangeContextValue,
    ChangeDetail,
)
from app.ui.dialogs.apply_changes_dialog import (
    ChangeDetailsDialog,
)


pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


def _summary():
    details = (
        ChangeDetail(
            session_row_id=1,
            context=(
                ChangeContextValue(
                    column="presupuestador",
                    label="Presupuestador",
                    value="Sandra",
                ),
                ChangeContextValue(
                    column="pais",
                    label="Pais",
                    value="PE",
                ),
                ChangeContextValue(
                    column="proveedor",
                    label="Proveedor",
                    value="Proveedor Uno",
                ),
            ),
            column="enero_usd",
            before=100,
            after=120,
            difference=None,
            variation_percent=None,
            change_type=(
                CHANGE_TYPE_EDITED
            ),
        ),
        ChangeDetail(
            session_row_id=2,
            context=(
                ChangeContextValue(
                    column="presupuestador",
                    label="Presupuestador",
                    value="Mauro",
                ),
                ChangeContextValue(
                    column="pais",
                    label="Pais",
                    value="CO",
                ),
                ChangeContextValue(
                    column="proveedor",
                    label="Proveedor",
                    value="Proveedor Dos",
                ),
            ),
            column="habilitado",
            before=True,
            after=False,
            difference=None,
            variation_percent=None,
            change_type=(
                CHANGE_TYPE_DISABLED
            ),
        ),
    )

    return SimpleNamespace(
        details=details,
        edited_rows=1,
        new_rows=0,
        disabled_rows=1,
        reactivated_rows=0,
    )


def test_details_dialog_shows_change_type(
    qapp,
):
    dialog = ChangeDetailsDialog(
        _summary(),
        "OPEX",
    )

    assert (
        dialog.detail_table
        .horizontalHeaderItem(0)
        .text()
        == "Tipo"
    )

    assert (
        dialog.detail_table
        .rowCount()
        == 2
    )

    values = {
        dialog.detail_table
        .item(row, 0)
        .data(
            Qt.ItemDataRole.UserRole
        )
        for row in range(
            dialog.detail_table
            .rowCount()
        )
    }

    assert values == {
        CHANGE_TYPE_EDITED,
        CHANGE_TYPE_DISABLED,
    }

    dialog.close()


def test_details_dialog_filters_by_type(
    qapp,
):
    dialog = ChangeDetailsDialog(
        _summary(),
        "OPEX",
    )

    index = (
        dialog.detail_type_filter
        .findData(
            CHANGE_TYPE_DISABLED
        )
    )

    assert index >= 0

    dialog.detail_type_filter.setCurrentIndex(
        index
    )

    QApplication.processEvents()

    visible = [
        row
        for row in range(
            dialog.detail_table
            .rowCount()
        )
        if not (
            dialog.detail_table
            .isRowHidden(row)
        )
    ]

    assert len(visible) == 1

    item = (
        dialog.detail_table
        .item(
            visible[0],
            0,
        )
    )

    assert (
        item.data(
            Qt.ItemDataRole.UserRole
        )
        == CHANGE_TYPE_DISABLED
    )

    dialog.close()


def test_details_dialog_searches_context(
    qapp,
):
    dialog = ChangeDetailsDialog(
        _summary(),
        "OPEX",
    )

    dialog.detail_search.setText(
        "Proveedor Uno"
    )

    QApplication.processEvents()

    visible = [
        row
        for row in range(
            dialog.detail_table
            .rowCount()
        )
        if not (
            dialog.detail_table
            .isRowHidden(row)
        )
    ]

    assert len(visible) == 1

    row = visible[0]

    row_values = {
        dialog.detail_table
        .item(
            row,
            column,
        )
        .text()
        for column in range(
            dialog.detail_table
            .columnCount()
        )
        if (
            dialog.detail_table
            .item(
                row,
                column,
            )
            is not None
        )
    }

    assert "Proveedor Uno" in row_values

    dialog.close()
