
from decimal import Decimal

import pytest

from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)
from app.services.new_budget_row_service import (
    NewBudgetRowService,
)
from app.services.presupuesto_change_summary_service import (
    PresupuestoChangeSummaryService,
)
from app.services.presupuesto_workspace import (
    SESSION_ROW_ID,
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_analysis_service import (
    PresupuestoWorkspaceAnalysisService,
)


pytestmark = pytest.mark.unit


def make_existing(
    index,
):
    row = {
        "row_id": f"row-{index}",
        "version": 1,
        "habilitado": True,
        "pais": "PER",
    }

    for column in (
        OPEX_MODULE_CONFIG
        .amount_columns
    ):
        row[column] = (
            Decimal("0.00")
        )

    return row


def make_new_draft():
    return (
        NewBudgetRowService(
            OPEX_MODULE_CONFIG,
            row_id_factory=(
                lambda: "new-ui-row"
            ),
        )
        .create_draft(
            {
                "pais": "PER",
                "presupuestador":
                    "M8D TEST",
                "nombre_gasto":
                    "NUEVA FILA GUI",
                "moneda_facturacion":
                    "USD",
            },
            actor="tester",
        )
    )


def test_new_row_is_available_on_last_page():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        (
            make_existing(0),
            make_existing(1),
            make_existing(2),
        )
    )

    session_id = (
        workspace.add_new_row(
            make_new_draft().row
        )
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    page = service.get_page(
        page_index=1,
        page_size=2,
    )

    assert page.total_rows == 4

    assert (
        page.rows[-1][
            SESSION_ROW_ID
        ]
        == session_id
    )


def test_change_summary_supports_new_row():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        ()
    )

    session_id = (
        workspace.add_new_row(
            make_new_draft().row
        )
    )

    workspace.edit_month(
        session_id,
        "enero_usd",
        Decimal("100.00"),
    )

    summary = (
        PresupuestoChangeSummaryService(
            workspace
        )
        .build()
    )

    assert summary.pending_rows == 1

    assert (
        summary.original_total
        == Decimal("0.00")
    )

    assert (
        summary.simulated_total
        == Decimal("100.00")
    )

    assert (
        summary.difference
        == Decimal("100.00")
    )

    assert any(
        detail.column
        == "enero_usd"
        and detail.before
        is None
        and detail.after
        == Decimal("100.00")
        for detail in summary.details
    )
