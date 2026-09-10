
from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
    USD_COLUMNS,
)


PENDING_STATUS = "PENDING"
APPLIED_STATUS = "APPLIED"
CONFLICT_STATUS = "CONFLICT"
FAILED_STATUS = "FAILED"

BATCH_STATUSES = (
    PENDING_STATUS,
    APPLIED_STATUS,
    CONFLICT_STATUS,
    FAILED_STATUS,
)


UPDATE_OPERATION = "UPDATE"
INSERT_OPERATION = "INSERT"

PERSISTENCE_OPERATIONS = (
    UPDATE_OPERATION,
    INSERT_OPERATION,
)


EDITABLE_COLUMNS = (
    HABILITADO_COLUMN,
    *USD_COLUMNS,
)


EDITABLE_VALUE_TYPES = {
    HABILITADO_COLUMN: "BOOLEAN",
    **{
        column: "NUMERIC"
        for column in USD_COLUMNS
    },
}


BUDGET_MODULE_COLUMN = (
    "budget_module"
)

REVERTED_BATCH_ID_COLUMN = (
    "reverted_batch_id"
)


BATCH_COLUMNS = (
    "batch_id",
    "status",
    "actor",
    "created_at",
    "completed_at",
    "row_count",
    "field_count",
    "app_version",
    "error_message",
    BUDGET_MODULE_COLUMN,
    REVERTED_BATCH_ID_COLUMN,
)


BATCH_TYPES = {
    "batch_id": "STRING",
    "status": "STRING",
    "actor": "STRING",
    "created_at": "TIMESTAMP",
    "completed_at": "TIMESTAMP",
    "row_count": "INTEGER",
    "field_count": "INTEGER",
    "app_version": "STRING",
    "error_message": "STRING",
    BUDGET_MODULE_COLUMN: "STRING",
    REVERTED_BATCH_ID_COLUMN: "STRING",
}


BATCH_NULLABLE_COLUMNS = (
    "completed_at",
    "app_version",
    "error_message",
    BUDGET_MODULE_COLUMN,
    REVERTED_BATCH_ID_COLUMN,
)


AUDIT_COLUMNS = (
    "audit_id",
    "batch_id",
    "row_id",
    "column_name",
    "value_type",
    "before_value",
    "after_value",
    "version_before",
    "version_after",
    "actor",
    "changed_at",
)


AUDIT_TYPES = {
    "audit_id": "STRING",
    "batch_id": "STRING",
    "row_id": "STRING",
    "column_name": "STRING",
    "value_type": "STRING",
    "before_value": "STRING",
    "after_value": "STRING",
    "version_before": "INTEGER",
    "version_after": "INTEGER",
    "actor": "STRING",
    "changed_at": "TIMESTAMP",
}


AUDIT_NULLABLE_COLUMNS = (
    "before_value",
    "after_value",
)


STAGING_OPERATION_COLUMN = (
    "operation"
)

STAGING_INSERT_PAYLOAD_COLUMN = (
    "insert_payload"
)


STAGING_COLUMNS = (
    "batch_id",
    "row_id",
    "expected_version",
    *EDITABLE_COLUMNS,
    "staged_at",
    STAGING_OPERATION_COLUMN,
    STAGING_INSERT_PAYLOAD_COLUMN,
)


STAGING_TYPES = {
    "batch_id": "STRING",
    "row_id": "STRING",
    "expected_version": "INTEGER",
    HABILITADO_COLUMN: "BOOLEAN",
    **{
        column: "NUMERIC"
        for column in USD_COLUMNS
    },
    "staged_at": "TIMESTAMP",
    STAGING_OPERATION_COLUMN:
        "STRING",
    STAGING_INSERT_PAYLOAD_COLUMN:
        "STRING",
}


STAGING_NULLABLE_COLUMNS = (
    *USD_COLUMNS,
    STAGING_OPERATION_COLUMN,
    STAGING_INSERT_PAYLOAD_COLUMN,
)
