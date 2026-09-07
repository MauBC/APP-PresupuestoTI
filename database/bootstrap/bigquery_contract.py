from google.cloud import bigquery

from database.bootstrap.persistence_enricher import (
    FINAL_STORAGE_COLUMNS,
    TECHNICAL_COLUMNS,
)
from database.bootstrap.schema import (
    STORAGE_AMOUNT_COLUMNS,
    STORAGE_STRING_COLUMNS,
)


TECHNICAL_TYPES = {
    "row_id": "STRING",
    "habilitado": "BOOLEAN",
    "version": "INTEGER",
    "created_at": "TIMESTAMP",
    "created_by": "STRING",
    "updated_at": "TIMESTAMP",
    "updated_by": "STRING",
}


BIGQUERY_STORAGE_TYPES = {
    **{
        column: "STRING"
        for column
        in STORAGE_STRING_COLUMNS
    },
    **{
        column: "NUMERIC"
        for column
        in STORAGE_AMOUNT_COLUMNS
    },
    **TECHNICAL_TYPES,
}


def build_bigquery_schema():
    fields = []

    for column in FINAL_STORAGE_COLUMNS:
        field_type = (
            BIGQUERY_STORAGE_TYPES[
                column
            ]
        )

        mode = (
            "REQUIRED"
            if column
            in TECHNICAL_COLUMNS
            else "NULLABLE"
        )

        fields.append(
            bigquery.SchemaField(
                column,
                field_type,
                mode=mode,
            )
        )

    return tuple(fields)


def build_bootstrap_load_config():
    config = (
        bigquery.LoadJobConfig()
    )

    config.schema = list(
        build_bigquery_schema()
    )

    config.autodetect = False

    config.write_disposition = (
        bigquery.WriteDisposition
        .WRITE_TRUNCATE
    )

    return config