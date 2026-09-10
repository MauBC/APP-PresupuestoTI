from decimal import Decimal

import pytest

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
    USD_MONTH_COLUMNS,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_analysis_service import (
    PresupuestoWorkspaceAnalysisService,
)


pytestmark = pytest.mark.unit


def make_row(
    *,
    gasto,
    pais="PERU",
    amount="100.00",
    enabled=None,
):
    row = {
        "nombre_gasto": gasto,
        "pais": pais,
        "presupuestador": "ANA",
    }

    for column in USD_MONTH_COLUMNS:
        row[column] = Decimal("0.00")

    row["enero_usd"] = Decimal(amount)
    row["anio_usd"] = Decimal(amount)

    if enabled is not None:
        row[HABILITADO_COLUMN] = enabled

    return row


def test_missing_habilitado_defaults_to_true():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="Servicio A",
            )
        ]
    )

    assert (
        workspace.get_row(0)[
            HABILITADO_COLUMN
        ]
        is True
    )


def test_disable_preserves_amounts():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="Servicio A",
                amount="100.00",
            )
        ]
    )

    workspace.set_enabled(
        0,
        False,
    )

    row = workspace.get_row(0)

    assert (
        row[HABILITADO_COLUMN]
        is False
    )

    assert (
        row["enero_usd"]
        == Decimal("100.00")
    )

    assert (
        row["anio_usd"]
        == Decimal("100.00")
    )

    assert workspace.pending_row_count == 1


def test_undo_restores_enabled_state():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="Servicio A",
            )
        ]
    )

    workspace.set_enabled(
        0,
        False,
    )

    workspace.undo_last()

    assert (
        workspace.get_row(0)[
            HABILITADO_COLUMN
        ]
        is True
    )

    assert not workspace.has_changes


def test_dashboard_excludes_disabled_rows():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="A",
                amount="100.00",
            ),
            make_row(
                gasto="B",
                amount="200.00",
            ),
        ]
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    before = service.get_dashboard()

    assert (
        before.total_usd
        == Decimal("300.00")
    )

    assert before.total_rows == 2

    workspace.set_enabled(
        1,
        False,
    )

    after = service.get_dashboard()

    assert (
        after.total_usd
        == Decimal("100.00")
    )

    assert after.total_rows == 1


def test_grouping_excludes_disabled_rows():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="A",
                amount="100.00",
            ),
            make_row(
                gasto="B",
                amount="200.00",
            ),
        ]
    )

    workspace.set_enabled(
        1,
        False,
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    result = service.get_grouped_totals(
        ("pais",)
    )

    peru = result.rows[0]

    assert peru["registros"] == 1

    assert (
        peru["anio_usd"]
        == Decimal("100.00")
    )


def test_page_still_contains_disabled_rows():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="A",
                amount="100.00",
            ),
            make_row(
                gasto="B",
                amount="200.00",
            ),
        ]
    )

    workspace.set_enabled(
        1,
        False,
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    result = service.get_page(
        page_index=0,
        page_size=100,
    )

    assert result.total_rows == 2
    assert len(result.rows) == 2

    assert (
        result.rows[1][
            HABILITADO_COLUMN
        ]
        is False
    )


def test_page_filters_enabled_rows():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="Activo",
                enabled=True,
            ),
            make_row(
                gasto="Inactivo",
                enabled=False,
            ),
        ]
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    result = service.get_page(
        page_index=0,
        page_size=100,
        enabled_filter="enabled",
    )

    assert result.total_rows == 1
    assert len(result.rows) == 1

    assert (
        result.rows[0][
            "nombre_gasto"
        ]
        == "Activo"
    )


def test_page_filters_disabled_rows():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="Activo",
                enabled=True,
            ),
            make_row(
                gasto="Inactivo",
                enabled=False,
            ),
        ]
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    result = service.get_page(
        page_index=0,
        page_size=100,
        enabled_filter="disabled",
    )

    assert result.total_rows == 1
    assert len(result.rows) == 1

    assert (
        result.rows[0][
            "nombre_gasto"
        ]
        == "Inactivo"
    )


def test_page_filter_happens_before_pagination():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="A",
                enabled=False,
            ),
            make_row(
                gasto="B",
                enabled=True,
            ),
            make_row(
                gasto="C",
                enabled=False,
            ),
            make_row(
                gasto="D",
                enabled=True,
            ),
            make_row(
                gasto="E",
                enabled=True,
            ),
        ]
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    result = service.get_page(
        page_index=1,
        page_size=2,
        enabled_filter="enabled",
    )

    assert result.total_rows == 3
    assert len(result.rows) == 1

    assert (
        result.rows[0][
            "nombre_gasto"
        ]
        == "E"
    )


def test_page_default_keeps_all_rows():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="Activo",
                enabled=True,
            ),
            make_row(
                gasto="Inactivo",
                enabled=False,
            ),
        ]
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    result = service.get_page(
        page_index=0,
        page_size=100,
    )

    assert result.total_rows == 2


def test_invalid_enabled_filter_is_rejected():
    workspace = PresupuestoWorkspace()

    workspace.load(
        [
            make_row(
                gasto="A",
            )
        ]
    )

    service = (
        PresupuestoWorkspaceAnalysisService(
            workspace
        )
    )

    with pytest.raises(
        ValueError,
        match="enabled_filter",
    ):
        service.get_page(
            page_index=0,
            page_size=100,
            enabled_filter="incorrecto",
        )
