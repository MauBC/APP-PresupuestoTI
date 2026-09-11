
from decimal import Decimal

import pytest

from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)
from app.services.new_budget_row_service import (
    NewBudgetRowService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
    PresupuestoWorkspaceError,
)


pytestmark = pytest.mark.unit


def make_draft(
    row_id,
):
    return (
        NewBudgetRowService(
            OPEX_MODULE_CONFIG,
            row_id_factory=(
                lambda:
                    row_id
            ),
        )
        .create_draft(
            {
                "pais": "PER",
                "nombre_gasto":
                    f"Gasto {row_id}",
                "moneda_facturacion":
                    "USD",
            },
            actor="tester",
        )
        .row
    )


def make_existing(
    row_id,
):
    row = {
        "row_id": row_id,
        "version": 1,
        "habilitado": True,
    }

    for column in (
        OPEX_MODULE_CONFIG
        .amount_columns
    ):
        row[column] = (
            Decimal("0.00")
        )

    return row


def test_bulk_add_creates_one_history_operation():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        ()
    )

    rows = tuple(
        make_draft(
            f"new-{index}"
        )
        for index in range(
            100
        )
    )

    session_ids = (
        workspace.add_new_rows(
            rows,
            description=(
                "Importar Excel"
            ),
        )
    )

    assert len(
        session_ids
    ) == 100

    assert (
        workspace.row_count
        == 100
    )

    assert (
        workspace.pending_row_count
        == 100
    )

    assert (
        workspace.history_count
        == 1
    )


def test_one_undo_removes_complete_import():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        ()
    )

    workspace.add_new_rows(
        (
            make_draft("a"),
            make_draft("b"),
            make_draft("c"),
        ),
        description=(
            "Importar Excel"
        ),
    )

    assert (
        workspace.undo_last()
    )

    assert (
        workspace.row_count
        == 0
    )

    assert not (
        workspace.has_changes
    )


def test_duplicate_inside_import_is_atomic():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        ()
    )

    with pytest.raises(
        PresupuestoWorkspaceError,
        match="ya existe",
    ):
        workspace.add_new_rows(
            (
                make_draft(
                    "duplicate"
                ),
                make_draft(
                    "duplicate"
                ),
            )
        )

    assert (
        workspace.row_count
        == 0
    )

    assert (
        workspace.history_count
        == 0
    )

    assert not (
        workspace.has_changes
    )


def test_collision_with_workspace_is_atomic():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        (
            make_existing(
                "existing"
            ),
        )
    )

    initial_rows = (
        workspace.row_count
    )

    with pytest.raises(
        PresupuestoWorkspaceError,
        match="ya existe",
    ):
        workspace.add_new_rows(
            (
                make_draft(
                    "new-ok"
                ),
                make_draft(
                    "existing"
                ),
            )
        )

    assert (
        workspace.row_count
        == initial_rows
    )

    assert (
        workspace.history_count
        == 0
    )

    assert not (
        workspace.has_changes
    )


def test_bulk_1000_rows_uses_single_history_batch():
    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        ()
    )

    rows = tuple(
        make_draft(
            f"bulk-{index}"
        )
        for index in range(
            1000
        )
    )

    workspace.add_new_rows(
        rows,
        description=(
            "Importar 1000 filas"
        ),
    )

    assert (
        workspace.row_count
        == 1000
    )

    assert (
        workspace.pending_row_count
        == 1000
    )

    assert (
        workspace.history_count
        == 1
    )
