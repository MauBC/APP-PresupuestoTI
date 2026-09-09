from types import SimpleNamespace

from datetime import (
    datetime,
    timezone,
)

import pytest

from app.ui.pages.history_page import (
    can_revert_history_batch,
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

def make_history_batch(
    *,
    batch_id="batch-001",
    status="APPLIED",
    reverted_batch_id=None,
):
    return SimpleNamespace(
        batch_id=batch_id,
        status=status,
        reverted_batch_id=(
            reverted_batch_id
        ),
    )


def test_applied_batch_can_be_reverted():
    batch = make_history_batch()

    assert can_revert_history_batch(
        batch,
        (batch,),
    )


def test_conflict_batch_cannot_be_reverted():
    batch = make_history_batch(
        status="CONFLICT"
    )

    assert not can_revert_history_batch(
        batch,
        (batch,),
    )


def test_reversal_batch_cannot_be_reverted():
    batch = make_history_batch(
        batch_id="reversal-001",
        reverted_batch_id="source-001",
    )

    assert not can_revert_history_batch(
        batch,
        (batch,),
    )


def test_already_reverted_source_is_disabled():
    source = make_history_batch(
        batch_id="source-001"
    )

    reversal = make_history_batch(
        batch_id="reversal-001",
        reverted_batch_id="source-001",
    )

    assert not can_revert_history_batch(
        source,
        (
            source,
            reversal,
        ),
    )


def test_other_reversal_does_not_block_batch():
    source = make_history_batch(
        batch_id="source-001"
    )

    other = make_history_batch(
        batch_id="reversal-002",
        reverted_batch_id="source-002",
    )

    assert can_revert_history_batch(
        source,
        (
            source,
            other,
        ),
    )
