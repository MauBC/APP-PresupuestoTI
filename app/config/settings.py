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

    BIGQUERY_CAPEX_TABLE = os.getenv(
        "BIGQUERY_CAPEX_TABLE",
        "capex_2027",
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

    # Microsoft Graph / SharePoint
    MS_TENANT_ID = (
        os.getenv(
            "MS_TENANT_ID",
            "",
        )
        .strip()
    )

    MS_CLIENT_ID = (
        os.getenv(
            "MS_CLIENT_ID",
            "",
        )
        .strip()
    )

    MS_CLIENT_SECRET = (
        os.getenv(
            "MS_CLIENT_SECRET",
            "",
        )
        .strip()
    )

    MS_GRAPH_SCOPE = (
        os.getenv(
            "MS_GRAPH_SCOPE",
            "https://graph.microsoft.com/.default",
        )
        .strip()
    )

    SHAREPOINT_HOSTNAME = (
        os.getenv(
            "SHAREPOINT_HOSTNAME",
            "",
        )
        .strip()
    )

    SHAREPOINT_SITE_PATH = (
        os.getenv(
            "SHAREPOINT_SITE_PATH",
            "",
        )
        .strip()
    )

    SHAREPOINT_CAPEX_LIST_NAME = (
        os.getenv(
            "SHAREPOINT_CAPEX_LIST_NAME",
            "Resumen_Capex",
        )
        .strip()
    )


    SHAREPOINT_OPEX_LIST_NAME = (
        os.getenv(
            "SHAREPOINT_OPEX_LIST_NAME",
            "Resumen_Opex",
        )
        .strip()
    )

    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 760

    SIDEBAR_WIDTH = 240


settings = Settings()
