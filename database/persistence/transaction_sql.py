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


def _audit_struct(
    *,
    column,
    value_type,
):
    return f"""
            STRUCT(
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
                target.`{column}`
                    IS DISTINCT FROM
                stage.`{column}`
                    AS changed
            )
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

    audit_structs = []

    for column in EDITABLE_COLUMNS:
        audit_structs.append(
            _audit_struct(
                column=column,
                value_type=(
                    EDITABLE_VALUE_TYPES[
                        column
                    ]
                ),
            )
        )

    audit_array = (
        ",\n\n            ".join(
            audit_structs
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
DECLARE v_staging_distinct_count INT64 DEFAULT 0;
DECLARE v_conflict_count INT64 DEFAULT 0;
DECLARE v_audit_row_count INT64 DEFAULT 0;
DECLARE v_updated_row_count INT64 DEFAULT 0;

BEGIN

    BEGIN TRANSACTION;

    SET (
        v_batch_row_count,
        v_batch_field_count,
        v_staging_row_count,
        v_staging_distinct_count,
        v_conflict_count
    ) = (

        SELECT AS STRUCT
            batch_info.row_count,
            batch_info.field_count,
            staging_info.row_count,
            staging_info.distinct_row_count,
            conflict_info.conflict_count

        FROM (

            SELECT
                IF(
                    COUNT(*) = 1,
                    ANY_VALUE(row_count),
                    NULL
                ) AS row_count,

                IF(
                    COUNT(*) = 1,
                    ANY_VALUE(field_count),
                    NULL
                ) AS field_count

            FROM `{batch_table}`

            WHERE
                batch_id = @batch_id
                AND status = 'PENDING'

        ) AS batch_info

        CROSS JOIN (

            SELECT
                COUNT(*) AS row_count,
                COUNT(DISTINCT row_id)
                    AS distinct_row_count

            FROM `{staging_table}`

            WHERE
                batch_id = @batch_id

        ) AS staging_info

        CROSS JOIN (

            SELECT
                COUNT(*) AS conflict_count

            FROM `{staging_table}` AS stage

            LEFT JOIN `{main_table}` AS target
                ON target.row_id = stage.row_id

            WHERE
                stage.batch_id = @batch_id
                AND (
                    target.row_id IS NULL
                    OR target.version
                        != stage.expected_version
                )

        ) AS conflict_info
    );

    IF v_batch_row_count IS NULL THEN
        RAISE USING MESSAGE =
            'Batch must exist exactly once and be PENDING.';
    END IF;

    IF (
        v_batch_field_count IS NULL
        OR v_batch_field_count <= 0
    ) THEN
        RAISE USING MESSAGE =
            'Batch field_count must be greater than zero.';
    END IF;

    IF (
        v_staging_row_count
        != v_batch_row_count
    ) THEN
        RAISE USING MESSAGE =
            'Staging row count does not match batch row_count.';
    END IF;

    IF (
        v_staging_distinct_count
        != v_staging_row_count
    ) THEN
        RAISE USING MESSAGE =
            'Staging contains duplicate row_id values.';
    END IF;

    IF v_conflict_count > 0 THEN

        CREATE TEMP TABLE
            persistence_conflicts
        AS

        SELECT
            stage.row_id,
            stage.expected_version,
            target.version
                AS current_version

        FROM `{staging_table}` AS stage

        LEFT JOIN `{main_table}` AS target
            ON target.row_id
                = stage.row_id

        WHERE
            stage.batch_id = @batch_id
            AND (
                target.row_id IS NULL
                OR target.version
                    != stage.expected_version
            );

        UPDATE `{batch_table}`

        SET
            status = 'CONFLICT',
            completed_at =
                CURRENT_TIMESTAMP(),
            error_message = FORMAT(
                'Optimistic concurrency conflict in %d row(s).',
                v_conflict_count
            )

        WHERE
            batch_id = @batch_id
            AND status = 'PENDING';

        IF @@row_count != 1 THEN
            RAISE USING MESSAGE =
                'Conflict batch status update failed.';
        END IF;

        DELETE FROM `{staging_table}`
        WHERE
            batch_id = @batch_id;

        COMMIT TRANSACTION;

        SELECT
            'CONFLICT' AS status,
            v_batch_row_count
                AS row_count,
            v_batch_field_count
                AS field_count,
            row_id,
            expected_version,
            current_version,
            CAST(NULL AS STRING)
                AS error_message

        FROM persistence_conflicts

        ORDER BY
            row_id;

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

        SELECT
            GENERATE_UUID()
                AS audit_id,
            @batch_id
                AS batch_id,
            target.row_id,
            change.column_name,
            change.value_type,
            change.before_value,
            change.after_value,
            target.version
                AS version_before,
            target.version + 1
                AS version_after,
            @actor
                AS actor,
            CURRENT_TIMESTAMP()
                AS changed_at

        FROM `{main_table}` AS target

        INNER JOIN `{staging_table}` AS stage
            ON target.row_id
                = stage.row_id
            AND target.version
                = stage.expected_version

        CROSS JOIN UNNEST([
            {audit_array}
        ]) AS change

        WHERE
            stage.batch_id = @batch_id
            AND change.changed;

        SET v_audit_row_count =
            @@row_count;

        IF (
            v_audit_row_count
            != v_batch_field_count
        ) THEN
            RAISE USING MESSAGE =
                'Audit row count does not match batch field_count.';
        END IF;

        MERGE `{main_table}` AS target

        USING (

            SELECT *
            FROM `{staging_table}`

            WHERE
                batch_id = @batch_id

        ) AS stage

        ON
            target.row_id
                = stage.row_id
            AND target.version
                = stage.expected_version

        WHEN MATCHED THEN
            UPDATE SET
                {merge_set};

        SET v_updated_row_count =
            @@row_count;

        IF (
            v_updated_row_count
            != v_batch_row_count
        ) THEN
            RAISE USING MESSAGE =
                'Updated row count does not match batch row_count.';
        END IF;

        UPDATE `{batch_table}`

        SET
            status = 'APPLIED',
            completed_at =
                CURRENT_TIMESTAMP(),
            error_message = NULL

        WHERE
            batch_id = @batch_id
            AND status = 'PENDING';

        IF @@row_count != 1 THEN
            RAISE USING MESSAGE =
                'Applied batch status update failed.';
        END IF;

        DELETE FROM `{staging_table}`

        WHERE
            batch_id = @batch_id;

        COMMIT TRANSACTION;

        SELECT
            'APPLIED' AS status,
            v_batch_row_count
                AS row_count,
            v_batch_field_count
                AS field_count,
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
