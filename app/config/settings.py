import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    APP_NAME = "APP Presupuesto TI"
    APP_VERSION = "0.1.0"

    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "")
    BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE", "")

    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 760

    SIDEBAR_WIDTH = 240


settings = Settings()
