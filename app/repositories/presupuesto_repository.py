from app.services.bigquery_service import BigQueryService


class PresupuestoRepository:
    def __init__(self, bigquery_service: BigQueryService):
        self._bigquery = bigquery_service

    def get_connection_status(self) -> bool:
        return self._bigquery.test_connection()
