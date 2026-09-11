from types import SimpleNamespace

import pytest

from app.ui.dialogs.history_detail_dialog import (
    audit_change_type_code,
    format_audit_display,
    format_audit_field,
)
from app.ui.pages.history_page import (
    can_revert_history_batch,
    format_history_operation,
    format_history_relation,
)


pytestmark = pytest.mark.unit


def batch(
    *,
    batch_id="batch-1",
    status="APPLIED",
    reverted_batch_id=None,
    reversal_batch_id=None,
    is_insert=False,
):
    return SimpleNamespace(
        batch_id=batch_id,
        status=status,
        reverted_batch_id=(
            reverted_batch_id
        ),
        reversal_batch_id=(
            reversal_batch_id
        ),
        is_insert=is_insert,
    )


def change(
    *,
    column="enero_usd",
    before="100",
    after="200",
    version_before=1,
):
    return SimpleNamespace(
        column_name=column,
        before_value=before,
        after_value=after,
        version_before=version_before,
    )


def test_normal_batch_is_change():
    item = batch()

    assert (
        format_history_operation(
            item
        )
        == "CAMBIO"
    )

    assert can_revert_history_batch(
        item
    )


def test_insert_batch_is_addition():
    item = batch(
        is_insert=True
    )

    assert (
        format_history_operation(
            item
        )
        == "ALTA"
    )

    assert can_revert_history_batch(
        item
    )


def test_reverted_insert_keeps_reverted_priority():
    item = batch(
        is_insert=True,
        reversal_batch_id="reversal-1",
    )

    assert (
        format_history_operation(
            item
        )
        == "REVERTIDO"
    )


def test_source_batch_knows_reversal():
    item = batch(
        reversal_batch_id="reversal-1"
    )

    assert (
        format_history_operation(
            item
        )
        == "REVERTIDO"
    )

    assert (
        format_history_relation(
            item
        )
        == "Revertido por: reversal-1"
    )

    assert not can_revert_history_batch(
        item
    )


def test_reversal_batch_knows_source():
    item = batch(
        batch_id="reversal-1",
        reverted_batch_id="source-1",
    )

    assert (
        format_history_operation(
            item
        )
        == "REVERSION"
    )

    assert (
        format_history_relation(
            item
        )
        == "Revierte: source-1"
    )

    assert not can_revert_history_batch(
        item
    )


def test_insert_audit_is_new():
    item = change(
        version_before=0
    )

    assert (
        audit_change_type_code(
            item
        )
        == "NEW"
    )


def test_disable_audit_is_detected():
    item = change(
        column="habilitado",
        before="true",
        after="false",
    )

    assert (
        audit_change_type_code(
            item
        )
        == "DISABLED"
    )


def test_reactivate_audit_is_detected():
    item = change(
        column="habilitado",
        before="false",
        after="true",
    )

    assert (
        audit_change_type_code(
            item
        )
        == "REACTIVATED"
    )


def test_reversal_batch_overrides_field_type():
    item = change(
        column="habilitado",
        before="true",
        after="false",
    )

    source = batch(
        reverted_batch_id="source-1"
    )

    assert (
        audit_change_type_code(
            item,
            source,
        )
        == "REVERSAL"
    )


def test_habilitado_field_has_business_label():
    assert (
        format_audit_field(
            "habilitado"
        )
        == "Estado"
    )


def test_usd_is_formatted_as_money():
    assert (
        format_audit_display(
            "1234.5",
            "NUMERIC",
            "enero_usd",
        )
        == "US$ 1,234.50"
    )


def test_boolean_is_business_text():
    assert (
        format_audit_display(
            "false",
            "BOOLEAN",
            "habilitado",
        )
        == "Deshabilitado"
    )
