from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
    PresupuestoWorkspaceError,
)
from app.services.presupuesto_workspace_loader import (
    PresupuestoWorkspaceLoader,
)


pytestmark = pytest.mark.unit


def make_row(
    row_id,
    *,
    version=1,
    enero="10.00",
):
    row = {
        "row_id": row_id,
        "version": version,
        "habilitado": True,
        "nombre_gasto": (
            f"Servicio {row_id}"
        ),
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal(
            "0.00"
        )

    row["enero_usd"] = Decimal(
        enero
    )

    row["febrero_usd"] = Decimal(
        "30.00"
    )

    row["anio_usd"] = (
        row["enero_usd"]
        + row["febrero_usd"]
    )

    return row


class FakeRepository:
    def __init__(
        self,
        persisted_rows,
    ):
        self.persisted_rows = {
            row["row_id"]: row
            for row in persisted_rows
        }

        self.requested_ids = None

    def get_rows_by_ids(
        self,
        row_ids,
    ):
        self.requested_ids = tuple(
            row_ids
        )

        return tuple(
            self.persisted_rows[
                row_id
            ]
            for row_id in row_ids
            if row_id
            in self.persisted_rows
        )


def test_reload_only_pending_rows():
    workspace = (
        PresupuestoWorkspace()
    )

    workspace.load(
        (
            make_row("r1"),
            make_row("r2"),
        )
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("20.00"),
    )

    repository = FakeRepository(
        (
            make_row(
                "r1",
                version=2,
                enero="20.00",
            ),
            make_row("r2"),
        )
    )

    loader = (
        PresupuestoWorkspaceLoader(
            repository,
            workspace,
        )
    )

    result = (
        loader.reload_pending_rows()
    )

    assert (
        repository.requested_ids
        == ("r1",)
    )

    assert result.row_count == 1

    assert (
        workspace.get_row(
            0
        )["version"]
        == 2
    )

    assert (
        workspace.get_row(
            0
        )["enero_usd"]
        == Decimal("20.00")
    )

    assert (
        workspace.get_row(
            1
        )["version"]
        == 1
    )

    assert not workspace.has_changes
    assert workspace.history_count == 0


def test_missing_persisted_row_is_rejected():
    workspace = (
        PresupuestoWorkspace()
    )

    workspace.load(
        (
            make_row("r1"),
        )
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("20.00"),
    )

    repository = (
        FakeRepository(())
    )

    loader = (
        PresupuestoWorkspaceLoader(
            repository,
            workspace,
        )
    )

    with pytest.raises(
        PresupuestoWorkspaceError,
        match="todas las filas",
    ):
        loader.reload_pending_rows()

    assert workspace.has_changes
