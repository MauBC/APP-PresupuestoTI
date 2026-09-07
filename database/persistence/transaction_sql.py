from database.persistence.contract import (
    EDITABLE_COLUMNS,
    EDITABLE_VALUE_TYPES,
)


class TransactionSqlError(
    ValueError
):
    pass


def _required_table_id(
    value,
    field_name,
):
    text = str(
        value
        if value is not None
        else ""
    ).strip()

    if not text:
        raise TransactionSqlError(
            f"{field_name} no puede estar vacio."
        )

    return text


def _audit_select(
    *,
    main_table_id,
    staging_table_id,
    column,
    value_type,
):
    return f"""
        SELECT
            GENERATE_UUID() AS audit_id,
            @batch_id AS batch_id,
            target.row_id AS row_id,
            '{column}' AS column_name,
            '{value_type}' AS value_type,
            CAST(
                target.`{column}`
                AS STRING
            ) AS before_value,
            CAST(
                stage.`{column}`
                AS STRING
            ) AS after_value,
            target.version
                AS version_before,
            target.version + 1
                AS version_after,
            @actor AS actor,
            CURRENT_TIMESTAMP()
                AS changed_at
        FROM `{main_table_id}` AS target
        INNER JOIN `{staging_table_id}` AS stage
            ON target.row_id = stage.row_id
            AND target.version = stage.expected_version
        WHERE
            stage.batch_id = @batch_id
            AND target.`{column}`
                IS DISTINCT FROM
                stage.`{column}`
    """.strip()


def build_apply_staged_batch_sql(
    *,
    main_table_id,
    batch_table_id,
    audit_table_id,
    staging_table_id,
):
    main_table = _required_table_id(
        main_table_id,
        "main_table_id",
    )

    batch_table = _required_table_id(
        batch_table_id,
        "batch_table_id",
    )

    audit_table = _required_table_id(
        audit_table_id,
        "audit_table_id",
    )

    staging_table = _required_table_id(
        staging_table_id,
        "staging_table_id",
    )

    audit_selects = []

    for column in EDITABLE_COLUMNS:
        audit_selects.append(
            _audit_select(
                main_table_id=main_table,
                staging_table_id=staging_table,
                column=column,
                value_type=(
                    EDITABLE_VALUE_TYPES[
                        column
                    ]
                ),
            )
        )

    audit_union = (
        "\n\n        UNION ALL\n\n"
        .join(
            audit_selects
        )
    )

    merge_assignments = [
        (
            f"`{column}` = "
            f"stage.`{column}`"
        )
        for column
        in EDITABLE_COLUMNS
    ]

    merge_assignments.extend(
        (
            "version = "
            "target.version + 1",
            "updated_at = "
            "CURRENT_TIMESTAMP()",
            "updated_by = "
            "@actor",
        )
    )

    merge_set = (
        ",\n                ".join(
            merge_assignments
        )
    )

    return f"""
DECLARE v_batch_row_count INT64;
DECLARE v_batch_field_count INT64;
DECLARE v_staging_row_count INT64 DEFAULT 0;
DECLARE v_conflict_count INT64 DEFAULT 0;
DECLARE v_audit_row_count INT64 DEFAULT 0;

BEGIN

    BEGIN TRANSACTION;

    SET (
        v_batch_row_count,
        v_batch_field_count
    ) = (
        SELECT AS STRUCT
            IF(
                COUNT(*) = 1,
                ANY_VALUE(row_count),
                NULL
            ),
            IF(
                COUNT(*) = 1,
                ANY_VALUE(field_count),
                NULL
            )
        FROM `{batch_table}`
        WHERE
            batch_id = @batch_id
            AND status = 'PENDING'
    );

    ASSERT
        v_batch_row_count IS NOT NULL
    AS
        'Batch must exist exactly once and be PENDING.';

    ASSERT
        v_batch_field_count IS NOT NULL
        AND v_batch_field_count > 0
    AS
        'Batch field_count must be greater than zero.';

    SET v_staging_row_count = (
        SELECT COUNT(*)
        FROM `{staging_table}`
        WHERE batch_id = @batch_id
    );

    ASSERT
        v_staging_row_count = v_batch_row_count
    AS
        'Staging row count does not match batch row_count.';

    ASSERT (
        SELECT
            COUNT(*) = COUNT(DISTINCT row_id)
        FROM `{staging_table}`
        WHERE batch_id = @batch_id
    )
    AS
        'Staging contains duplicate row_id values.';

    CREATE TEMP TABLE persistence_conflicts AS
    SELECT
        stage.row_id,
        stage.expected_version,
        target.version AS current_version
    FROM `{staging_table}` AS stage
    LEFT JOIN `{main_table}` AS target
        ON target.row_id = stage.row_id
    WHERE
        stage.batch_id = @batch_id
        AND (
            target.row_id IS NULL
            OR target.version
                != stage.expected_version
        );

    SET v_conflict_count = (
        SELECT COUNT(*)
        FROM persistence_conflicts
    );

    IF v_conflict_count > 0 THEN

        UPDATE `{batch_table}`
        SET
            status = 'CONFLICT',
            completed_at = CURRENT_TIMESTAMP(),
            error_message = FORMAT(
                'Optimistic concurrency conflict in %d row(s).',
                v_conflict_count
            )
        WHERE
            batch_id = @batch_id
            AND status = 'PENDING';

        DELETE FROM `{staging_table}`
        WHERE batch_id = @batch_id;

        COMMIT TRANSACTION;

        SELECT
            'CONFLICT' AS status,
            v_batch_row_count AS row_count,
            v_batch_field_count AS field_count,
            row_id,
            expected_version,
            current_version,
            CAST(NULL AS STRING)
                AS error_message
        FROM persistence_conflicts
        ORDER BY row_id;

    ELSE

        INSERT INTO `{audit_table}` (
            audit_id,
            batch_id,
            row_id,
            column_name,
            value_type,
            before_value,
            after_value,
            version_before,
            version_after,
            actor,
            changed_at
        )

        {audit_union};

        SET v_audit_row_count = (
            SELECT COUNT(*)
            FROM `{audit_table}`
            WHERE batch_id = @batch_id
        );

        ASSERT
            v_audit_row_count
                = v_batch_field_count
        AS
            'Audit row count does not match batch field_count.';

        MERGE `{main_table}` AS target

        USING (
            SELECT *
            FROM `{staging_table}`
            WHERE batch_id = @batch_id
        ) AS stage

        ON
            target.row_id = stage.row_id
            AND target.version
                = stage.expected_version

        WHEN MATCHED THEN
            UPDATE SET
                {merge_set};

        UPDATE `{batch_table}`
        SET
            status = 'APPLIED',
            completed_at = CURRENT_TIMESTAMP(),
            error_message = NULL
        WHERE
            batch_id = @batch_id
            AND status = 'PENDING';

        DELETE FROM `{staging_table}`
        WHERE batch_id = @batch_id;

        COMMIT TRANSACTION;

        SELECT
            'APPLIED' AS status,
            v_batch_row_count AS row_count,
            v_batch_field_count AS field_count,
            CAST(NULL AS STRING)
                AS row_id,
            CAST(NULL AS INT64)
                AS expected_version,
            CAST(NULL AS INT64)
                AS current_version,
            CAST(NULL AS STRING)
                AS error_message;

    END IF;

EXCEPTION WHEN ERROR THEN

    ROLLBACK TRANSACTION;

    SELECT
        'FAILED' AS status,
        COALESCE(
            v_batch_row_count,
            0
        ) AS row_count,
        COALESCE(
            v_batch_field_count,
            0
        ) AS field_count,
        CAST(NULL AS STRING)
            AS row_id,
        CAST(NULL AS INT64)
            AS expected_version,
        CAST(NULL AS INT64)
            AS current_version,
        @@error.message
            AS error_message;

END;
""".strip()
