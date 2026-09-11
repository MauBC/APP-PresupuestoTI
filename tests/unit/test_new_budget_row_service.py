from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.services.new_budget_row_service import (
    NewBudgetRowError,
    NewBudgetRowService,
)


pytestmark = pytest.mark.unit


NOW = datetime(
    2026,
    9,
    9,
    20,
    0,
    tzinfo=timezone.utc,
)


def test_opex_draft_has_technical_defaults():
    service = NewBudgetRowService(
        OPEX_MODULE_CONFIG,
        row_id_factory=(
            lambda: "new-opex-001"
        ),
    )

    draft = service.create_draft(
        {
            "pais": " PER ",
            "presupuestador":
                "Mauro",
            "nombre_gasto":
                "Licencias",
        },
        actor="tester",
        timestamp=NOW,
    )

    assert (
        draft.module
        == "OPEX"
    )

    assert (
        draft.row_id
        == "new-opex-001"
    )

    assert draft.version == 1
    assert draft.enabled

    assert (
        draft.row["pais"]
        == "PER"
    )

    assert (
        draft.row["created_by"]
        == "tester"
    )

    assert (
        draft.row["updated_by"]
        == "tester"
    )

    assert (
        draft.row["created_at"]
        == NOW
    )

    for column in (
        OPEX_MODULE_CONFIG
        .amount_columns
    ):
        assert (
            draft.row[column]
            == Decimal("0.00")
        )


def test_capex_draft_uses_capex_dimensions():
    service = NewBudgetRowService(
        CAPEX_MODULE_CONFIG,
        row_id_factory=(
            lambda: "new-capex-001"
        ),
    )

    draft = service.create_draft(
        {
            "pais": "PER",
            "sociedad":
                "Ransa Peru",
            "responsable":
                "Mauro",
            "anio": 2027,
            "cantidad": 1,
            "nombre_inversion":
                "Proyecto nuevo",
        },
        actor="tester",
        timestamp=NOW,
    )

    assert (
        draft.module
        == "CAPEX"
    )

    assert (
        draft.row["anio"]
        == 2027
    )

    assert (
        draft.row["cantidad"]
        == 1
    )

    assert (
        draft.row[
            "presupuestador"
        ]
        is None
    )

    for column in (
        CAPEX_MODULE_CONFIG
        .amount_columns
    ):
        assert (
            draft.row[column]
            == Decimal("0.00")
        )


def test_unknown_dimension_is_rejected():
    service = NewBudgetRowService(
        CAPEX_MODULE_CONFIG
    )

    with pytest.raises(
        NewBudgetRowError,
        match="no validas",
    ):
        service.create_draft(
            {
                "dimension_inexistente":
                    "No aplica",
            },
            actor="tester",
            timestamp=NOW,
        )


def test_empty_actor_is_rejected():
    service = NewBudgetRowService(
        OPEX_MODULE_CONFIG
    )

    with pytest.raises(
        NewBudgetRowError,
        match="actor",
    ):
        service.create_draft(
            {},
            actor="  ",
            timestamp=NOW,
        )


def test_naive_timestamp_is_rejected():
    service = NewBudgetRowService(
        OPEX_MODULE_CONFIG
    )

    with pytest.raises(
        NewBudgetRowError,
        match="zona horaria",
    ):
        service.create_draft(
            {},
            actor="tester",
            timestamp=(
                datetime(
                    2026,
                    9,
                    9,
                    20,
                    0,
                )
            ),
        )
