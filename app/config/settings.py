import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    APP_NAME = "APP Presupuesto TI"
    APP_VERSION = "0.5.0"

    GOOGLE_CLOUD_PROJECT = os.getenv(
        "GOOGLE_CLOUD_PROJECT",
        "",
    )

    BIGQUERY_DATASET = os.getenv(
        "BIGQUERY_DATASET",
        "",
    )

    BIGQUERY_TABLE = os.getenv(
        "BIGQUERY_TABLE",
        "",
    )

    BIGQUERY_LOCATION = os.getenv(
        "BIGQUERY_LOCATION",
        "US",
    )

    BIGQUERY_BATCH_TABLE = os.getenv(
        "BIGQUERY_BATCH_TABLE",
        "presupuesto_change_batches",
    )

    BIGQUERY_AUDIT_TABLE = os.getenv(
        "BIGQUERY_AUDIT_TABLE",
        "presupuesto_audit",
    )

    BIGQUERY_STAGING_TABLE = os.getenv(
        "BIGQUERY_STAGING_TABLE",
        "presupuesto_change_staging",
    )

    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 760

    SIDEBAR_WIDTH = 240


settings = Settings()