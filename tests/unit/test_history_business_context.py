from datetime import (
    datetime,
    timezone,
)

import pytest

from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)
from app.models.budget_history import (
    BudgetHistoryBatch,
)
from app.services.presupuesto_history_service import (
    PresupuestoHistoryService,
)
from app.ui.dialogs.history_detail_dialog import (
    build_detail_headers,
    build_enhanced_detail_rows,
)


pytestmark = pytest.mark.unit


NOW = datetime(
    2026,
    9,
    10,
    20,
    0,
    tzinfo=timezone.utc,
)


def make_batch():
    return BudgetHistoryBatch(
        batch_id="batch-context",
        status="APPLIED",
        actor="tester",
        created_at=NOW,
        completed_at=NOW,
        row_count=1,
        field_count=1,
        app_version="test",
        error_message=None,
        budget_module="OPEX",
    )


class FakeRepository:
    module_config = (
        OPEX_MODULE_CONFIG
    )

    def get_batch_audit(
        self,
        batch_id,
    ):
        return (
            {
                "audit_id": "audit-1",
                "batch_id": batch_id,
                "row_id": "row-001",
                "column_name":
                    "enero_usd",
                "value_type":
                    "NUMERIC",
                "before_value":
                    "100.00",
                "after_value":
                    "150.00",
                "version_before": 1,
                "version_after": 2,
                "actor": "tester",
                "changed_at": NOW,
            },
        )

    def get_history_row_context(
        self,
        row_ids,
    ):
        assert tuple(
            row_ids
        ) == (
            "row-001",
        )

        return (
            {
                "row_id":
                    "row-001",
                "presupuestador":
                    "SANDRA",
                "pais":
                    "PERU",
                "compania":
                    "RANSA PERU",
                "proveedor":
                    "MICROSOFT",
                "nombre_gasto":
                    "LICENCIAS M365",
                "ceco":
                    "CECO-100",
            },
        )


def make_detail():
    return (
        PresupuestoHistoryService(
            FakeRepository()
        )
        .get_batch_detail(
            make_batch()
        )
    )


def test_context_values_are_available():
    detail = make_detail()

    assert (
        detail.context_value(
            "row-001",
            "presupuestador",
        )
        == "SANDRA"
    )

    assert (
        detail.context_value(
            "row-001",
            "proveedor",
        )
        == "MICROSOFT"
    )

    assert (
        detail.context_value(
            "row-001",
            "nombre_gasto",
        )
        == "LICENCIAS M365"
    )

    assert (
        detail.context_value(
            "row-001",
            "ceco",
        )
        == "CECO-100"
    )


def test_business_columns_precede_row_id():
    detail = make_detail()

    headers = (
        build_detail_headers(
            detail
        )
    )

    assert (
        headers[0]
        == "TIPO"
    )

    assert (
        "PRESUPUESTADOR"
        in headers
    )

    assert (
        "PROVEEDOR"
        in headers
    )

    assert (
        "NOMBRE DEL GASTO"
        in headers
    )

    assert (
        "CECO"
        in headers
    )

    assert (
        headers[-1]
        == "ROW ID"
    )


def test_detail_row_is_business_readable():
    detail = make_detail()

    headers = (
        build_detail_headers(
            detail
        )
    )

    values = (
        build_enhanced_detail_rows(
            detail
        )[0][:-1]
    )

    row = dict(
        zip(
            headers,
            values,
        )
    )

    assert (
        row[
            "PRESUPUESTADOR"
        ]
        == "SANDRA"
    )

    assert (
        row[
            "PROVEEDOR"
        ]
        == "MICROSOFT"
    )

    assert (
        row[
            "NOMBRE DEL GASTO"
        ]
        == "LICENCIAS M365"
    )

    assert (
        row["CECO"]
        == "CECO-100"
    )

    assert (
        row["CAMPO"]
        == "Enero USD"
    )

    assert (
        row["ANTES"]
        == "US$ 100.00"
    )

    assert (
        row["DESPUES"]
        == "US$ 150.00"
    )

    assert (
        row["ROW ID"]
        == "row-001"
    )
