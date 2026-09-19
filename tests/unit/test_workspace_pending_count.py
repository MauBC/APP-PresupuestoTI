from decimal import Decimal

import pytest

from app.config.budget_modules import OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG
from app.services.new_budget_row_service import NewBudgetRowService
from app.services.presupuesto_workspace import PresupuestoWorkspace, PresupuestoWorkspaceError

pytestmark = pytest.mark.unit


@pytest.fixture(params=[OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG])
def workspace(request):
    config = request.param
    workspace = PresupuestoWorkspace(config)
    workspace.load([{**{column: Decimal("0") for column in config.amount_columns},
                     "row_id": "existing", "version": 1, "notes": {"items": ["original"]}}])
    return workspace


def assert_count_matches_detail(workspace):
    assert workspace.pending_change_count == sum(len(row.changes) for row in workspace.get_pending_changes())


def test_counter_tracks_edit_revert_disable_undo_discard_and_reload(workspace):
    month = workspace.module_config.month_columns[0]
    assert workspace.pending_change_count == 0
    workspace.edit_month(0, month, Decimal("12.50"))
    assert workspace.pending_change_count == 2
    workspace.set_enabled(0, False)
    assert workspace.pending_change_count == 3
    assert_count_matches_detail(workspace)
    workspace.undo_last()
    assert workspace.pending_change_count == 2
    workspace.edit_month(0, month, Decimal("0"))
    assert workspace.pending_change_count == 0
    workspace.undo_last()
    assert workspace.pending_change_count == 2
    workspace.discard_all()
    assert workspace.pending_change_count == 0
    workspace.set_enabled(0, False)
    workspace.load([])
    assert workspace.pending_change_count == 0


def test_counter_matches_bulk_insert_and_undo(workspace):
    draft = NewBudgetRowService(workspace.module_config).create_draft({}, actor="tester").row
    workspace.add_new_rows((draft,), description="Test import")
    assert workspace.pending_change_count > 0
    assert_count_matches_detail(workspace)
    workspace.undo_last()
    assert workspace.pending_change_count == 0


def test_counter_does_not_build_audit_and_detail_still_copies_values(workspace, monkeypatch):
    updated = workspace.get_row(0)
    updated["notes"] = {"items": ["changed"]}
    updated["extra"] = "added"
    workspace.apply_batch(description="Change metadata", replacements={0: updated})
    detail = workspace.get_pending_changes()
    assert_count_matches_detail(workspace)
    def unexpected():
        raise AssertionError("A counter must not construct the audit detail")
    monkeypatch.setattr(workspace, "get_pending_changes", unexpected)
    assert workspace.pending_change_count == 2
    notes = next(change for change in detail[0].changes if change.column == "notes")
    notes.after["items"].append("external mutation")
    notes.before["items"].append("external mutation")
    assert workspace.get_row(0)["notes"] == {"items": ["changed"]}
    assert workspace.get_original_row(0)["notes"] == {"items": ["original"]}


def test_unloaded_workspace_counter_keeps_error_contract():
    with pytest.raises(PresupuestoWorkspaceError):
        _ = PresupuestoWorkspace().pending_change_count
