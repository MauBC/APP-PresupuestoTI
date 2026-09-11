from google.cloud import bigquery

from app.config.capex_schema import (
    CAPEX_EXPECTED_COLUMNS,
    CAPEX_EXPECTED_TYPES,
)
from app.config.presupuesto_schema import (
    PERSISTENCE_COLUMNS,
)


CAPEX_REQUIRED_COLUMNS = frozenset(
    PERSISTENCE_COLUMNS
)


def build_capex_bigquery_schema():
    fields = []

    for column in (
        CAPEX_EXPECTED_COLUMNS
    ):
        field_type = (
            CAPEX_EXPECTED_TYPES[
                column
            ]
        )

        mode = (
            "REQUIRED"
            if column
            in CAPEX_REQUIRED_COLUMNS
            else "NULLABLE"
        )

        fields.append(
            bigquery.SchemaField(
                column,
                field_type,
                mode=mode,
            )
        )

    return tuple(
        fields
    )


def build_capex_bootstrap_load_config():
    config = (
        bigquery.LoadJobConfig()
    )

    config.schema = list(
        build_capex_bigquery_schema()
    )

    config.autodetect = False

    config.write_disposition = (
        bigquery.WriteDisposition
        .WRITE_TRUNCATE
    )

    return config


def build_capex_append_load_config():
    config = (
        bigquery.LoadJobConfig()
    )

    config.schema = list(
        build_capex_bigquery_schema()
    )

    config.autodetect = False

    config.write_disposition = (
        bigquery.WriteDisposition
        .WRITE_APPEND
    )

    return config
