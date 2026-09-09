from datetime import (
    datetime,
    timezone,
)

import pytest

from app.ui.pages.history_page import (
    format_history_datetime,
    format_history_status,
)


pytestmark = pytest.mark.unit


def test_history_status_labels():
    assert (
        format_history_status(
            "APPLIED"
        )
        == "APLICADO"
    )

    assert (
        format_history_status(
            "CONFLICT"
        )
        == "CONFLICTO"
    )

    assert (
        format_history_status(
            "FAILED"
        )
        == "ERROR"
    )


def test_unknown_status_is_preserved():
    assert (
        format_history_status(
            "CUSTOM"
        )
        == "CUSTOM"
    )


def test_none_datetime_is_empty():
    assert (
        format_history_datetime(
            None
        )
        == ""
    )


def test_datetime_is_formatted():
    value = datetime(
        2026,
        9,
        8,
        20,
        30,
        15,
        tzinfo=timezone.utc,
    )

    result = (
        format_history_datetime(
            value
        )
    )

    assert (
        result
        .count("/")
        == 2
    )

    assert ":" in result
