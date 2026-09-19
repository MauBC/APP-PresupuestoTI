from decimal import Decimal

import pytest

from app.config.budget_modules import OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG
from app.services import presupuesto_workspace as workspace_module
from app.services.new_budget_row_service import NewBudgetRowService
from app.services.presupuesto_workspace import PresupuestoWorkspace

pytestmark = pytest.mark.unit


@pytest.fixture(params=[OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG])
def workspace(request):
    config = request.param
    workspace = PresupuestoWorkspace(config)
    workspace.load([
        {**{column: Decimal("0") for column in config.amount_columns},
         "row_id": str(index), "version": 1, "notes": {"items": ["original"]}}
        for index in range(3)
    ])
    return workspace


def test_discard_restores_edits_removes_new_rows_and_clears_history(workspace):
    original = workspace.get_rows()
    workspace.edit_month(0, workspace.module_config.month_columns[0], Decimal("10"))
    workspace.set_enabled(1, False)
    draft = NewBudgetRowService(workspace.module_config).create_draft({}, actor="tester").row
    workspace.add_new_rows((draft,), description="Import test")
    workspace.discard_all()
    assert workspace.get_rows() == original
    assert workspace.history_count == workspace.pending_row_count == workspace.pending_change_count == 0
    assert not workspace.undo_last()
    workspace.discard_all()
    assert workspace.get_rows() == original
    workspace.edit_month(0, workspace.module_config.month_columns[0], Decimal("20"))
    assert workspace.get_original_row(0) == original[0]
    workspace.undo_last()
    assert workspace.get_rows() == original


def test_discard_copies_only_changed_originals_and_keeps_nested_values_independent(workspace, monkeypatch):
    row = workspace.get_row(0)
    row["notes"] = {"items": ["changed"]}
    workspace.apply_batch(description="Edit metadata", replacements={0: row})
    copied = []
    deepcopy = workspace_module.deepcopy
    def counted(value):
        copied.append(value)
        return deepcopy(value)
    monkeypatch.setattr(workspace_module, "deepcopy", counted)
    workspace.discard_all()
    assert len(copied) == 1
    assert copied[0]["row_id"] == "0"
    # Even nested original values must remain independent of the working copy.
    workspace._working_rows[0]["notes"]["items"].append("changed again")
    assert workspace.get_original_row(0)["notes"] == {"items": ["original"]}


def test_failed_copy_does_not_partially_discard(workspace, monkeypatch):
    workspace.set_enabled(0, False)
    workspace.set_enabled(1, False)
    before = workspace.get_rows()
    history_count = workspace.history_count
    deepcopy = workspace_module.deepcopy
    calls = []
    def fail_second(value):
        calls.append(value)
        if len(calls) == 2:
            raise RuntimeError("copy failed")
        return deepcopy(value)
    with monkeypatch.context() as patch:
        patch.setattr(workspace_module, "deepcopy", fail_second)
        with pytest.raises(RuntimeError, match="copy failed"):
            workspace.discard_all()
    assert workspace.get_rows() == before
    assert workspace.history_count == history_count
    assert workspace.pending_row_count == 2


def test_discard_clears_history_even_when_edits_cancel_each_other(workspace):
    workspace.set_enabled(0, False)
    workspace.set_enabled(0, True)
    assert workspace.pending_row_count == 0 and workspace.history_count == 2
    workspace.discard_all()
    assert workspace.history_count == 0
