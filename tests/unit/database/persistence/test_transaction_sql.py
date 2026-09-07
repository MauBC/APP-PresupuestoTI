import pytest

from app.config.presupuesto_app_config import (
    USD_COLUMNS,
)
from database.persistence.transaction_sql import (
    TransactionSqlError,
    build_apply_staged_batch_sql,
)


pytestmark = pytest.mark.unit


def build_sql():
    return build_apply_staged_batch_sql(
        main_table_id=(
            "project.dataset."
            "presupuesto_2026"
        ),
        batch_table_id=(
            "project.dataset."
            "presupuesto_change_batches"
        ),
        audit_table_id=(
            "project.dataset."
            "presupuesto_audit"
        ),
        staging_table_id=(
            "project.dataset."
            "presupuesto_change_staging"
        ),
    )


def test_transaction_boundaries_exist():
    sql = build_sql()

    assert (
        "BEGIN TRANSACTION;"
        in sql
    )

    assert (
        "COMMIT TRANSACTION;"
        in sql
    )

    assert (
        "ROLLBACK TRANSACTION;"
        in sql
    )


def test_conflict_detection_uses_row_id_and_version():
    sql = build_sql()

    assert (
        "target.row_id = stage.row_id"
        in sql
    )

    assert (
        "target.version"
        in sql
    )

    assert (
        "stage.expected_version"
        in sql
    )

    assert (
        "'CONFLICT' AS status"
        in sql
    )


def test_missing_target_is_a_conflict():
    sql = build_sql()

    assert (
        "LEFT JOIN"
        in sql
    )

    assert (
        "target.row_id IS NULL"
        in sql
    )


def test_staging_count_is_validated():
    sql = build_sql()

    assert (
        "v_staging_row_count"
        in sql
    )

    assert (
        "Staging row count does not match"
        in sql
    )


def test_duplicate_staging_row_ids_are_rejected():
    sql = build_sql()

    assert (
        "COUNT(DISTINCT row_id)"
        in sql
    )

    assert (
        "Staging contains duplicate row_id"
        in sql
    )


def test_audit_is_inserted_before_merge():
    sql = build_sql()

    audit_position = sql.index(
        "INSERT INTO "
        "`project.dataset."
        "presupuesto_audit`"
    )

    merge_position = sql.index(
        "MERGE "
        "`project.dataset."
        "presupuesto_2026`"
    )

    assert (
        audit_position
        < merge_position
    )


def test_audit_contains_all_editable_columns():
    sql = build_sql()

    assert (
        "'habilitado' AS column_name"
        in sql
    )

    for column in USD_COLUMNS:
        assert (
            f"'{column}' AS column_name"
            in sql
        )


def test_audit_uses_is_distinct_from():
    sql = build_sql()

    assert (
        sql.count(
            "IS DISTINCT FROM"
        )
        == 14
    )


def test_merge_updates_all_editable_values():
    sql = build_sql()

    assert (
        "`habilitado` = "
        "stage.`habilitado`"
        in sql
    )

    for column in USD_COLUMNS:
        assert (
            f"`{column}` = "
            f"stage.`{column}`"
            in sql
        )


def test_merge_increments_version():
    sql = build_sql()

    assert (
        "version = "
        "target.version + 1"
        in sql
    )


def test_merge_updates_actor_and_timestamp():
    sql = build_sql()

    assert (
        "updated_at = "
        "CURRENT_TIMESTAMP()"
        in sql
    )

    assert (
        "updated_by = @actor"
        in sql
    )


def test_success_marks_batch_applied():
    sql = build_sql()

    assert (
        "status = 'APPLIED'"
        in sql
    )

    assert (
        "'APPLIED' AS status"
        in sql
    )


def test_conflict_cleans_staging():
    sql = build_sql()

    conflict_position = (
        sql.index(
            "status = 'CONFLICT'"
        )
    )

    delete_position = (
        sql.index(
            "DELETE FROM "
            "`project.dataset."
            "presupuesto_change_staging`",
            conflict_position,
        )
    )

    assert (
        delete_position
        > conflict_position
    )


def test_no_physical_delete_from_main():
    sql = build_sql()

    assert (
        "DELETE FROM "
        "`project.dataset."
        "presupuesto_2026`"
        not in sql
    )


def test_transaction_never_uses_write_truncate():
    sql = build_sql()

    assert (
        "WRITE_TRUNCATE"
        not in sql
    )


@pytest.mark.parametrize(
    "argument",
    (
        "main_table_id",
        "batch_table_id",
        "audit_table_id",
        "staging_table_id",
    ),
)
def test_empty_table_id_is_rejected(
    argument,
):
    values = {
        "main_table_id": "a.b.main",
        "batch_table_id": "a.b.batch",
        "audit_table_id": "a.b.audit",
        "staging_table_id": "a.b.stage",
    }

    values[
        argument
    ] = " "

    with pytest.raises(
        TransactionSqlError,
        match="vacio",
    ):
        build_apply_staged_batch_sql(
            **values
        )


def test_audit_count_is_validated_before_merge():
    sql = build_sql()

    assert (
        "v_audit_row_count"
        in sql
    )

    assert (
        "Audit row count does not match"
        in sql
    )

    audit_check_position = sql.index(
        "SET v_audit_row_count"
    )

    merge_position = sql.index(
        "MERGE "
        "`project.dataset."
        "presupuesto_2026`"
    )

    assert (
        audit_check_position
        < merge_position
    )


def test_merge_left_side_is_not_target_qualified():
    sql = build_sql()

    assert (
        "`enero_usd` = "
        "stage.`enero_usd`"
        in sql
    )

    assert (
        "target.`enero_usd` = "
        "stage.`enero_usd`"
        not in sql
    )

    assert (
        "version = "
        "target.version + 1"
        in sql
    )

