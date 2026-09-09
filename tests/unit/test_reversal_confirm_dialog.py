from datetime import (
    datetime,
    timezone,
)

import pytest

from app.ui.dialogs.reversal_confirm_dialog import (
    REVERSAL_CONFIRMATION_TEXT,
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
