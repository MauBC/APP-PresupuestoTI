from datetime import (
    datetime,
    timezone,
)

import pytest

from app.ui.dialogs.reversal_confirm_dialog import (
    REVERSAL_CONFIRMATION_TEXT,
    build_reversal_applied_impact,
    build_reversal_safety_text,
    build_reversal_summary,
    format_reversal_datetime,
    is_reversal_confirmation_valid,
)


pytestmark = pytest.mark.unit


def test_confirmation_constant():
    assert (
        REVERSAL_CONFIRMATION_TEXT
        == "REVERTIR"
    )


@pytest.mark.parametrize(
    "value",
    (
        "REVERTIR",
        "revertir",
        "  REVERTIR  ",
    ),
)
def test_valid_confirmation(
    value,
):
    assert (
        is_reversal_confirmation_valid(
            value
        )
    )


@pytest.mark.parametrize(
    "value",
    (
        "",
        None,
        "CONFIRMAR",
        "REVERTI",
        "REVERTIR AHORA",
    ),
)
def test_invalid_confirmation(
    value,
):
    assert not (
        is_reversal_confirmation_valid(
            value
        )
    )


def test_reversal_datetime():
    value = datetime(
        2026,
        9,
        8,
        21,
        30,
        0,
        tzinfo=timezone.utc,
    )

    result = (
        format_reversal_datetime(
            value
        )
    )

    assert "/" in result
    assert ":" in result


def test_safety_text_explains_logical_disable():
    text = (
        build_reversal_safety_text()
    )

    assert (
        "NO realiza DELETE"
        in text
    )

    assert (
        "DESHABILITARAN"
        in text
    )

    assert (
        "baja logica"
        in text
    )

    assert (
        "concurrencia"
        in text
    )


def test_summary_uses_business_labels():
    batch = type(
        "Batch",
        (),
        {
            "batch_id":
                "batch-001",
            "created_at":
                datetime(
                    2026,
                    9,
                    10,
                    20,
                    0,
                    tzinfo=timezone.utc,
                ),
            "actor":
                "usuario",
            "budget_module":
                "CAPEX",
            "row_count":
                4,
            "field_count":
                9,
        },
    )()

    text = (
        build_reversal_summary(
            batch
        )
    )

    assert "batch-001" in text
    assert "CAPEX" in text

    assert (
        "Filas afectadas"
        in text
    )

    assert (
        "Cambios registrados"
        in text
    )


def test_applied_impact_distinguishes_inserts():
    def change(
        row_id,
        version_before,
    ):
        return type(
            "Change",
            (),
            {
                "row_id":
                    row_id,
                "version_before":
                    version_before,
            },
        )()

    detail = type(
        "Detail",
        (),
        {
            "changes": (
                change(
                    "row-update",
                    2,
                ),
                change(
                    "row-insert-1",
                    0,
                ),
                change(
                    "row-insert-1",
                    0,
                ),
                change(
                    "row-insert-2",
                    0,
                ),
            )
        },
    )()

    result = type(
        "Result",
        (),
        {
            "row_count": 3,
            "field_count": 4,
        },
    )()

    text = (
        build_reversal_applied_impact(
            detail,
            result,
        )
    )

    assert (
        "Filas procesadas: 3"
        in text
    )

    assert (
        "Filas con valores "
        "restaurados: 1"
        in text
    )

    assert (
        "Filas nuevas "
        "deshabilitadas: 2"
        in text
    )

    assert (
        "Cambios compensatorios: 4"
        in text
    )

    assert (
        "NO fueron eliminadas "
        "fisicamente"
        in text
    )


def test_applied_impact_without_inserts():
    detail = type(
        "Detail",
        (),
        {
            "changes": (
                type(
                    "Change",
                    (),
                    {
                        "row_id":
                            "row-1",
                        "version_before":
                            3,
                    },
                )(),
            )
        },
    )()

    result = type(
        "Result",
        (),
        {
            "row_count": 1,
            "field_count": 2,
        },
    )()

    text = (
        build_reversal_applied_impact(
            detail,
            result,
        )
    )

    assert (
        "Filas con valores "
        "restaurados: 1"
        in text
    )

    assert (
        "Filas nuevas "
        "deshabilitadas"
        not in text
    )
