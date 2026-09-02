from app.models.page_result import PageResult
from app.services.bigquery_service import BigQueryService


class PresupuestoRepository:
    def __init__(
        self,
        bigquery_service: BigQueryService,
    ):
        self._bigquery = bigquery_service

    def get_connection_status(self) -> bool:
        return self._bigquery.test_connection()

    def get_page(
        self,
        *,
        limit: int,
        offset: int,
    ) -> PageResult:
        table = self._bigquery.get_table()

        columns = tuple(
            field.name
            for field in table.schema
        )

        rows_iterator = (
            self._bigquery.client.list_rows(
                table,
                start_index=offset,
                max_results=limit,
            )
        )

        rows = []

        for row in rows_iterator:
            values = dict(row.items())

            rows.append(
                {
                    column: values.get(column)
                    for column in columns
                }
            )

        page_index = (
            offset // limit
            if limit > 0
            else 0
        )

        return PageResult(
            rows=tuple(rows),
            columns=columns,
            total_rows=table.num_rows,
            page_index=page_index,
            page_size=limit,
        )