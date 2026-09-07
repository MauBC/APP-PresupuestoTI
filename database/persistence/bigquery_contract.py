from dataclasses import dataclass

from google.cloud import bigquery

from app.config.settings import settings
from database.persistence.contract import (
    AUDIT_COLUMNS,
    AUDIT_NULLABLE_COLUMNS,
    AUDIT_TYPES,
    BATCH_COLUMNS,
    BATCH_NULLABLE_COLUMNS,
    BATCH_TYPES,
    STAGING_COLUMNS,
    STAGING_NULLABLE_COLUMNS,
    STAGING_TYPES,
)


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceTableSpec:
    table_name: str
    schema: tuple[
        bigquery.SchemaField,
        ...
    ]

    def table_id(
        self,
        *,
        project: str,
        dataset: str,
    ) -> str:
        return (
            f"{project}."
            f"{dataset}."
            f"{self.table_name}"
        )


def _build_schema(
    *,
    columns,
    types,
    nullable_columns,
):
    nullable = set(
        nullable_columns
    )

    return tuple(
        bigquery.SchemaField(
            column,
            types[column],
            mode=(
                "NULLABLE"
                if column in nullable
                else "REQUIRED"
            ),
        )
        for column in columns
    )


def build_batch_schema():
    return _build_schema(
        columns=BATCH_COLUMNS,
        types=BATCH_TYPES,
        nullable_columns=(
            BATCH_NULLABLE_COLUMNS
        ),
    )


def build_audit_schema():
    return _build_schema(
        columns=AUDIT_COLUMNS,
        types=AUDIT_TYPES,
        nullable_columns=(
            AUDIT_NULLABLE_COLUMNS
        ),
    )


def build_staging_schema():
    return _build_schema(
        columns=STAGING_COLUMNS,
        types=STAGING_TYPES,
        nullable_columns=(
            STAGING_NULLABLE_COLUMNS
        ),
    )


def build_persistence_table_specs():
    return (
        PersistenceTableSpec(
            table_name=(
                settings
                .BIGQUERY_BATCH_TABLE
            ),
            schema=(
                build_batch_schema()
            ),
        ),
        PersistenceTableSpec(
            table_name=(
                settings
                .BIGQUERY_AUDIT_TABLE
            ),
            schema=(
                build_audit_schema()
            ),
        ),
        PersistenceTableSpec(
            table_name=(
                settings
                .BIGQUERY_STAGING_TABLE
            ),
            schema=(
                build_staging_schema()
            ),
        ),
    )
