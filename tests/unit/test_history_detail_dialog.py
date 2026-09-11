from datetime import (
    datetime,
    timezone,
)
from types import SimpleNamespace

import pytest

from app.ui.dialogs.history_detail_dialog import (
    build_detail_rows,
    format_audit_value,
    format_detail_datetime,
)


pytestmark = pytest.mark.unit


def test_null_audit_value_is_empty():
    assert (
        format_audit_value(
            None
        )
        == ""
    )


def test_audit_value_is_text():
    assert (
        format_audit_value(
            "125.00"
        )
        == "125.00"
    )


def test_detail_datetime_is_formatted():
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
        format_detail_datetime(
            value
        )
    )

    assert "/" in result
    assert ":" in result


def test_build_detail_rows():
    changed_at = datetime(
        2026,
        9,
        8,
        20,
        0,
        tzinfo=timezone.utc,
    )

    detail = SimpleNamespace(
        changes=(
            SimpleNamespace(
                row_id="row-001",
                column_name=(
                    "enero_usd"
                ),
                before_value="100.00",
                after_value="125.00",
                version_before=1,
                version_after=2,
                actor="PC\\Mauro",
                changed_at=(
                    changed_at
                ),
            ),
        )
    )

    rows = build_detail_rows(
        detail
    )

    assert len(rows) == 1

    row = rows[0]

    assert (
        row[0]
        == "row-001"
    )

    assert (
        row[1]
        == "enero_usd"
    )

    assert (
        row[2]
        == "100.00"
    )

    assert (
        row[3]
        == "125.00"
    )

    assert row[4] == 1
    assert row[5] == 2

    assert (
        row[6]
        == "PC\\Mauro"
    )
