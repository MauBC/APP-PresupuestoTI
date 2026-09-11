from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from itertools import count

import pytest

from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)
from app.services.new_budget_row_service import (
    NewBudgetRowService,
)
from app.services.opex_smart_inference_service import (
    OpexSmartInferenceService,
)
from app.services.opex_smart_insert_service import (
    OpexSmartInsertError,
    OpexSmartInsertService,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)


pytestmark = pytest.mark.unit


NOW = datetime(
    2026,
    9,
    11,
    18,
    0,
    tzinfo=timezone.utc,
)


def historical_row(
    *,
    ceco,
    pais="PER",
    gasto="LICENCIAS",
    proveedor="MICROSOFT",
    categoria="SOFTWARE",
    enabled=True,
):
    row = {
        column:
            f"value-{column}"
        for column in (
            OPEX_MODULE_CONFIG
            .dimension_columns
        )
    }

    row.update(
        {
            "ceco":
                ceco,
            "pais":
                pais,
            "nombre_gasto":
                gasto,
            "proveedor":
                proveedor,
            "categoria_gasto":
                categoria,
            "periodo":
                "2026",
            "habilitado":
                enabled,
        }
    )

    return row


class FakeInferenceDataService:
    def __init__(
        self,
        rows,
    ):
        self._rows = tuple(
            rows
        )

        self._engine = (
            OpexSmartInferenceService()
        )

    def infer(
        self,
        known_values,
    ):
        return self._engine.infer(
            known_values,
            self._rows,
        )


def build_service(
    rows,
):
    sequence = count(
        1
    )

    row_service = (
        NewBudgetRowService(
            OPEX_MODULE_CONFIG,
            row_id_factory=(
                lambda:
                    f"smart-{next(sequence)}"
            ),
        )
    )

    return OpexSmartInsertService(
        FakeInferenceDataService(
            rows
        ),
        row_service=row_service,
    )


def default_history():
    return (
        historical_row(
            ceco="001001",
        ),
        historical_row(
            ceco="001002",
        ),
        historical_row(
            ceco="001003",
        ),
    )


def base_dimensions():
    return {
        "nombre_gasto":
            "LICENCIAS",
    }


def two_month_pattern():
    result = {
        column:
            Decimal("0.00")
        for column in (
            OPEX_MODULE_CONFIG
            .month_columns
        )
    }

    result[
        "enero_usd"
    ] = Decimal("50.00")

    result[
        "febrero_usd"
    ] = Decimal("50.00")

    return result


def test_percentage_mode_generates_three_rows():
    service = build_service(
        default_history()
    )

    preview = (
        service
        .preview_percentages(
            base_dimensions=(
                base_dimensions()
            ),
            allocations=(
                (
                    ("001001", "20"),
                    ("001002", "30"),
                    ("001003", "50"),
                )
            ),
            annual_total="1000",
            actor="tester",
            timestamp=NOW,
        )
    )

    assert preview.is_ready
    assert preview.row_count == 3
    assert preview.ready_count == 3
    assert preview.blocked_count == 0

    assert (
        preview.source_total
        == Decimal("1000.00")
    )

    assert (
        preview.allocated_total
        == Decimal("1000.00")
    )

    amounts = {
        item.ceco:
            item.annual_total
        for item in preview.items
    }

    assert amounts == {
        "001001":
            Decimal("200.00"),
        "001002":
            Decimal("300.00"),
        "001003":
            Decimal("500.00"),
    }


def test_default_monthly_pattern_keeps_annual_totals():
    service = build_service(
        default_history()
    )

    preview = (
        service
        .preview_percentages(
            base_dimensions=(
                base_dimensions()
            ),
            allocations={
                "001001": "50",
                "001002": "50",
            },
            annual_total="100",
            actor="tester",
            timestamp=NOW,
        )
    )

    rows = service.build_rows(
        preview
    )

    assert len(rows) == 2

    for row in rows:
        monthly_total = sum(
            (
                row[column]
                for column in (
                    OPEX_MODULE_CONFIG
                    .month_columns
                )
            ),
            Decimal("0"),
        )

        assert (
            monthly_total
            == row["anio_usd"]
        )


def test_custom_monthly_pattern_is_applied_to_every_ceco():
    service = build_service(
        default_history()
    )

    preview = (
        service
        .preview_percentages(
            base_dimensions=(
                base_dimensions()
            ),
            allocations={
                "001001": "25",
                "001002": "75",
            },
            annual_total="400",
            monthly_percentages=(
                two_month_pattern()
            ),
            actor="tester",
            timestamp=NOW,
        )
    )

    rows = service.build_rows(
        preview
    )

    by_ceco = {
        row["ceco"]:
            row
        for row in rows
    }

    assert (
        by_ceco[
            "001001"
        ]["anio_usd"]
        == Decimal("100.00")
    )

    assert (
        by_ceco[
            "001001"
        ]["enero_usd"]
        == Decimal("50.00")
    )

    assert (
        by_ceco[
            "001001"
        ]["febrero_usd"]
        == Decimal("50.00")
    )

    assert (
        by_ceco[
            "001002"
        ]["anio_usd"]
        == Decimal("300.00")
    )

    assert (
        by_ceco[
            "001002"
        ]["enero_usd"]
        == Decimal("150.00")
    )

    assert (
        by_ceco[
            "001002"
        ]["febrero_usd"]
        == Decimal("150.00")
    )


def test_direct_amount_mode_uses_exact_values():
    service = build_service(
        default_history()
    )

    preview = (
        service
        .preview_amounts(
            base_dimensions=(
                base_dimensions()
            ),
            allocations=(
                (
                    ("001001", "10.01"),
                    ("001002", "20.02"),
                    ("001003", "30.03"),
                )
            ),
            actor="tester",
            timestamp=NOW,
        )
    )

    assert (
        preview.source_total
        == Decimal("60.06")
    )

    assert (
        preview.allocated_total
        == Decimal("60.06")
    )

    assert [
        item.annual_total
        for item in preview.items
    ] == [
        Decimal("10.01"),
        Decimal("20.02"),
        Decimal("30.03"),
    ]


def test_ceco_leading_zero_is_preserved():
    service = build_service(
        default_history()
    )

    preview = (
        service
        .preview_amounts(
            base_dimensions=(
                base_dimensions()
            ),
            allocations={
                "001001":
                    "25.00",
            },
            actor="tester",
            timestamp=NOW,
        )
    )

    row = (
        service
        .build_rows(
            preview
        )[0]
    )

    assert row["ceco"] == "001001"


def test_percentage_total_must_be_exactly_100():
    service = build_service(
        default_history()
    )

    with pytest.raises(
        OpexSmartInsertError,
        match="100.00",
    ):
        service.preview_percentages(
            base_dimensions=(
                base_dimensions()
            ),
            allocations={
                "001001": "50",
                "001002": "40",
            },
            annual_total="100",
            actor="tester",
            timestamp=NOW,
        )


def test_duplicate_ceco_is_rejected():
    service = build_service(
        default_history()
    )

    with pytest.raises(
        OpexSmartInsertError,
        match="duplicado",
    ):
        service.preview_amounts(
            base_dimensions=(
                base_dimensions()
            ),
            allocations=(
                (
                    "001001",
                    "10",
                ),
                (
                    "001001",
                    "20",
                ),
            ),
            actor="tester",
            timestamp=NOW,
        )


def test_negative_amount_is_rejected():
    service = build_service(
        default_history()
    )

    with pytest.raises(
        OpexSmartInsertError,
        match="negativo",
    ):
        service.preview_amounts(
            base_dimensions=(
                base_dimensions()
            ),
            allocations={
                "001001":
                    "-1",
            },
            actor="tester",
            timestamp=NOW,
        )


def test_unknown_ceco_blocks_generation():
    service = build_service(
        default_history()
    )

    preview = (
        service
        .preview_amounts(
            base_dimensions=(
                base_dimensions()
            ),
            allocations={
                "009999":
                    "100",
            },
            actor="tester",
            timestamp=NOW,
        )
    )

    assert not preview.is_ready
    assert preview.blocked_count == 1

    assert (
        "SIN_HISTORIAL"
        in preview
        .items[0]
        .blockers
    )

    with pytest.raises(
        OpexSmartInsertError,
        match="009999",
    ):
        service.build_rows(
            preview
        )


def test_ambiguous_history_blocks_until_user_resolves():
    rows = (
        historical_row(
            ceco="001001",
            proveedor="MICROSOFT",
        ),
        historical_row(
            ceco="001001",
            proveedor="ORACLE",
        ),
    )

    service = build_service(
        rows
    )

    blocked = (
        service
        .preview_amounts(
            base_dimensions={
                "nombre_gasto":
                    "LICENCIAS",
            },
            allocations={
                "001001":
                    "100",
            },
            actor="tester",
            timestamp=NOW,
        )
    )

    assert not blocked.is_ready

    assert (
        "proveedor"
        in blocked
        .items[0]
        .ambiguous_map
    )

    resolved = (
        service
        .preview_amounts(
            base_dimensions={
                "nombre_gasto":
                    "LICENCIAS",
                "proveedor":
                    "MICROSOFT",
            },
            allocations={
                "001001":
                    "100",
            },
            actor="tester",
            timestamp=NOW,
        )
    )

    assert resolved.is_ready

    row = (
        service
        .build_rows(
            resolved
        )[0]
    )

    assert (
        row["proveedor"]
        == "MICROSOFT"
    )


def test_workspace_bulk_insert_is_one_undoable_operation():
    service = build_service(
        default_history()
    )

    preview = (
        service
        .preview_percentages(
            base_dimensions=(
                base_dimensions()
            ),
            allocations={
                "001001": "20",
                "001002": "30",
                "001003": "50",
            },
            annual_total="1000",
            actor="tester",
            timestamp=NOW,
        )
    )

    workspace = (
        PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )
    )

    workspace.load(
        ()
    )

    service.add_to_workspace(
        preview,
        workspace,
        description=(
            "Alta inteligente prueba"
        ),
    )

    assert workspace.row_count == 3

    assert (
        workspace.pending_row_count
        == 3
    )

    assert (
        workspace.history_count
        == 1
    )

    assert workspace.has_changes

    assert workspace.undo_last()

    assert workspace.row_count == 0
    assert workspace.history_count == 0
    assert not workspace.has_changes


def test_generated_rows_have_insert_technical_contract():
    service = build_service(
        default_history()
    )

    preview = (
        service
        .preview_amounts(
            base_dimensions=(
                base_dimensions()
            ),
            allocations={
                "001001":
                    "100",
                "001002":
                    "200",
            },
            actor="tester",
            timestamp=NOW,
        )
    )

    rows = service.build_rows(
        preview
    )

    assert {
        row["row_id"]
        for row in rows
    } == {
        "smart-1",
        "smart-2",
    }

    for row in rows:
        assert row["version"] == 1
        assert row["habilitado"] is True
        assert row["created_at"] == NOW
        assert row["updated_at"] == NOW
        assert row["created_by"] == "tester"
        assert row["updated_by"] == "tester"


def test_ceco_cannot_be_supplied_in_base_dimensions():
    service = build_service(
        default_history()
    )

    with pytest.raises(
        OpexSmartInsertError,
        match="CECO",
    ):
        service.preview_amounts(
            base_dimensions={
                "nombre_gasto":
                    "LICENCIAS",
                "ceco":
                    "001001",
            },
            allocations={
                "001001":
                    "100",
            },
            actor="tester",
            timestamp=NOW,
        )
