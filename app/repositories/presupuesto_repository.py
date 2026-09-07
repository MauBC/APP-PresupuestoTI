from app.config.presupuesto_app_config import (
    APP_COLUMNS,
    GROUPABLE_COLUMNS,
    LOAD_COLUMNS,
    USD_COLUMNS,
)
from app.models.aggregation_result import AggregationResult
from app.models.dashboard_result import DashboardResult
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

    def get_all_rows(
        self,
    ) -> tuple[dict, ...]:
        table = self._bigquery.get_table()

        load_columns = set(
            LOAD_COLUMNS
        )

        selected_fields = tuple(
            field
            for field in table.schema
            if field.name in load_columns
        )

        selected_names = tuple(
            field.name
            for field in selected_fields
        )

        rows_iterator = (
            self._bigquery.client.list_rows(
                table,
                selected_fields=selected_fields,
            )
        )

        return tuple(
            {
                column: values.get(column)
                for column in selected_names
            }
            for values in (
                dict(row.items())
                for row in rows_iterator
            )
        )

    def get_page(
        self,
        *,
        limit: int,
        offset: int,
    ) -> PageResult:
        table = self._bigquery.get_table()

        app_columns = set(
            APP_COLUMNS
        )

        selected_fields = tuple(
            field
            for field in table.schema
            if field.name in app_columns
        )

        selected_names = tuple(
            field.name
            for field in selected_fields
        )

        rows_iterator = (
            self._bigquery.client.list_rows(
                table,
                selected_fields=selected_fields,
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
                    for column in selected_names
                }
            )

        page_index = (
            offset // limit
            if limit > 0
            else 0
        )

        return PageResult(
            rows=tuple(rows),
            columns=selected_names,
            total_rows=table.num_rows,
            page_index=page_index,
            page_size=limit,
        )

    def get_grouped_totals(
        self,
        group_columns: tuple[str, ...],
    ) -> AggregationResult:
        allowed_groups = set(
            GROUPABLE_COLUMNS
        )

        invalid_columns = [
            column
            for column in group_columns
            if column not in allowed_groups
        ]

        if invalid_columns:
            raise ValueError(
                "Columnas de agrupacion no validas: "
                + ", ".join(invalid_columns)
            )

        table_ref = (
            self._bigquery.get_table_reference()
        )

        group_select = ", ".join(
            f"`{column}`"
            for column in group_columns
        )

        usd_select = ",\n".join(
            (
                "SUM("
                f"COALESCE(`{column}`, NUMERIC '0')"
                f") AS `{column}`"
            )
            for column in USD_COLUMNS
        )

        sql = f"""
            SELECT
                {group_select},
                COUNT(*) AS registros,
                {usd_select}
            FROM `{table_ref}`
            WHERE COALESCE(`habilitado`, TRUE)
            GROUP BY {group_select}
            ORDER BY `anio_usd` DESC
        """

        query_result = (
            self._bigquery.client
            .query(sql)
            .result()
        )

        rows = tuple(
            dict(row.items())
            for row in query_result
        )

        columns = (
            *group_columns,
            "registros",
            *USD_COLUMNS,
        )

        return AggregationResult(
            rows=rows,
            columns=columns,
            group_columns=group_columns,
        )

    def get_dashboard(
        self,
    ) -> DashboardResult:
        table_ref = (
            self._bigquery.get_table_reference()
        )

        summary_sql = f"""
            SELECT
                COUNT(*) AS total_rows,

                COUNT(
                    DISTINCT NULLIF(
                        TRIM(`pais`),
                        ''
                    )
                ) AS total_countries,

                COUNT(
                    DISTINCT NULLIF(
                        TRIM(`presupuestador`),
                        ''
                    )
                ) AS total_budgeters,

                COALESCE(
                    SUM(
                        COALESCE(
                            `anio_usd`,
                            NUMERIC '0'
                        )
                    ),
                    NUMERIC '0'
                ) AS total_usd

            FROM `{table_ref}`
            WHERE COALESCE(`habilitado`, TRUE)
        """

        summary = next(
            self._bigquery.client
            .query(summary_sql)
            .result()
        )

        country_sql = f"""
            SELECT
                COALESCE(
                    NULLIF(TRIM(`pais`), ''),
                    '(Sin pais)'
                ) AS pais,

                COUNT(*) AS registros,

                COALESCE(
                    SUM(
                        COALESCE(
                            `anio_usd`,
                            NUMERIC '0'
                        )
                    ),
                    NUMERIC '0'
                ) AS total_usd

            FROM `{table_ref}`
            WHERE COALESCE(`habilitado`, TRUE)

            GROUP BY 1
            ORDER BY total_usd DESC
        """

        budgeter_sql = f"""
            SELECT
                COALESCE(
                    NULLIF(
                        TRIM(`presupuestador`),
                        ''
                    ),
                    '(Sin presupuestador)'
                ) AS presupuestador,

                COUNT(*) AS registros,

                COALESCE(
                    SUM(
                        COALESCE(
                            `anio_usd`,
                            NUMERIC '0'
                        )
                    ),
                    NUMERIC '0'
                ) AS total_usd

            FROM `{table_ref}`
            WHERE COALESCE(`habilitado`, TRUE)

            GROUP BY 1
            ORDER BY total_usd DESC
        """

        country_rows = tuple(
            dict(row.items())
            for row in (
                self._bigquery.client
                .query(country_sql)
                .result()
            )
        )

        budgeter_rows = tuple(
            dict(row.items())
            for row in (
                self._bigquery.client
                .query(budgeter_sql)
                .result()
            )
        )

        return DashboardResult(
            total_usd=summary["total_usd"],
            total_rows=summary["total_rows"],
            total_countries=summary["total_countries"],
            total_budgeters=summary["total_budgeters"],
            by_country=country_rows,
            by_budgeter=budgeter_rows,
        )