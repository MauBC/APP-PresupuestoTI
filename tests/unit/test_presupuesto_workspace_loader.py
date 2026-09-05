from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_loader import (
    PresupuestoWorkspaceLoader,
)


pytestmark = pytest.mark.unit


def make_row():
    row = {
        "nombre_gasto": "Servicio A",
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal("0.00")

    row["enero_usd"] = Decimal("10.00")
    row["febrero_usd"] = Decimal("30.00")
    row["anio_usd"] = Decimal("40.00")

    return row


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def get_all_rows(self):
        self.calls += 1
        return tuple(self.rows)


def test_loader_loads_repository_rows():
    repository = FakeRepository(
        [
            make_row(),
            make_row(),
        ]
    )

    workspace = PresupuestoWorkspace()

    loader = PresupuestoWorkspaceLoader(
        repository,
        workspace,
    )

    result = loader.load()

    assert repository.calls == 1
    assert result.row_count == 2
    assert workspace.row_count == 2
    assert workspace.is_loaded


def test_loader_starts_clean_workspace():
    repository = FakeRepository(
        [make_row()]
    )

    workspace = PresupuestoWorkspace()

    loader = PresupuestoWorkspaceLoader(
        repository,
        workspace,
    )

    loader.load()

    assert (
        workspace.pending_row_count
        == 0
    )

    assert (
        workspace.history_count
        == 0
    )

    assert not workspace.has_changes


def test_loader_result_contains_timings():
    repository = FakeRepository(
        [make_row()]
    )

    workspace = PresupuestoWorkspace()

    loader = PresupuestoWorkspaceLoader(
        repository,
        workspace,
    )

    result = loader.load()

    assert result.fetch_seconds >= 0
    assert result.workspace_seconds >= 0
    assert result.total_seconds >= 0

    assert (
        result.total_seconds
        >= result.fetch_seconds
    )