from decimal import Decimal

import pytest

from app.config.budget_modules import OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG
from app.services.presupuesto_workspace import PresupuestoWorkspace, SESSION_ROW_ID
from app.services.presupuesto_workspace_analysis_service import PresupuestoWorkspaceAnalysisService

pytestmark = pytest.mark.unit


@pytest.fixture(params=[OPEX_MODULE_CONFIG, CAPEX_MODULE_CONFIG])
def workspace(request):
    config = request.param
    result = PresupuestoWorkspace(config)
    result.load([
        {**{column: Decimal("0") for column in config.amount_columns}, "habilitado": i % 3 != 0}
        for i in range(23)
    ])
    return result


@pytest.mark.parametrize("filter_value", ["all", "enabled", "disabled"])
@pytest.mark.parametrize("page_size", [1, 5, 8, 23, 100])
def test_pages_match_current_rows_and_clamp_to_last(workspace, filter_value, page_size):
    service = PresupuestoWorkspaceAnalysisService(workspace)
    expected = [row[SESSION_ROW_ID] for row in workspace.iter_rows()
                if filter_value == "all" or row["habilitado"] == (filter_value == "enabled")]
    last = max(0, (len(expected) - 1) // page_size)
    for requested in (0, 1, last, last + 1, 999):
        page = service.get_page(page_index=requested, page_size=page_size, enabled_filter=filter_value)
        actual = min(requested, last)
        assert page.page_index == actual
        assert page.total_rows == len(expected)
        assert [row[SESSION_ROW_ID] for row in page.rows] == expected[actual * page_size:(actual + 1) * page_size]


def test_page_reads_only_needed_rows_and_filtered_fallback_scans_once(workspace, monkeypatch):
    original = workspace.iter_rows
    visited = []
    def counted():
        for row in original():
            visited.append(row[SESSION_ROW_ID])
            yield row
    monkeypatch.setattr(workspace, "iter_rows", counted)
    service = PresupuestoWorkspaceAnalysisService(workspace)
    service.get_page(page_index=0, page_size=5)
    assert visited == list(range(5))
    visited.clear()
    service.get_page(page_index=999, page_size=5, enabled_filter="enabled")
    assert visited == list(range(23))


@pytest.mark.parametrize("filter_value", ["all", "enabled", "disabled"])
def test_empty_workspace_and_no_matches(workspace, filter_value):
    workspace.load([])
    service = PresupuestoWorkspaceAnalysisService(workspace)
    page = service.get_page(page_index=999, page_size=5, enabled_filter=filter_value)
    assert (page.rows, page.total_rows, page.page_index) == ((), 0, 0)


def test_pages_reflect_edits_state_changes_and_reload(workspace):
    service = PresupuestoWorkspaceAnalysisService(workspace)
    month = workspace.module_config.month_columns[0]
    page = service.get_page(page_index=0, page_size=5)
    page.rows[0][month] = Decimal("999")
    assert workspace.get_row(0)[month] == 0
    workspace.edit_month(1, month, Decimal("42.50"))
    assert service.get_page(page_index=0, page_size=5).rows[1][month] == Decimal("42.50")
    before = service.get_page(page_index=0, page_size=5, enabled_filter="enabled")
    workspace.set_enabled(1, False)
    after = service.get_page(page_index=0, page_size=5, enabled_filter="enabled")
    assert after.total_rows == before.total_rows - 1
    assert 1 not in [row[SESSION_ROW_ID] for row in after.rows]
    workspace.load([])
    assert service.get_page(page_index=0, page_size=5).total_rows == 0
