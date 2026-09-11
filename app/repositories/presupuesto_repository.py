from google.cloud import bigquery

from app.config.budget_module_config import (
    BudgetModuleConfig,
)
from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)

from app.config.presupuesto_app_config import (
    APP_COLUMNS,
    GROUPABLE_COLUMNS,
    LOAD_COLUMNS,
)
from app.models.aggregation_result import AggregationResult
from app.models.dashboard_result import DashboardResult
from app.models.page_result import PageResult
from app.services.bigquery_service import BigQueryService


class PresupuestoRepository:
    def __init__(
        self,
        bigquery_service: BigQueryService,
        module_config:
            BudgetModuleConfig | None = None,
    ):
        self._bigquery = bigquery_service

        self._module_config = (
            module_config
            if module_config is not None
            else OPEX_MODULE_CONFIG
        )

    @property
    def module_config(
        self,
    ) -> BudgetModuleConfig:
        return self._module_config

    @property
    def app_columns(
        self,
    ) -> tuple[str, ...]:
        return (
            *self._module_config
            .insert_columns,
            "habilitado",
        )
    @property
    def load_columns(
        self,
    ) -> tuple[str, ...]:
        return (
            *self._module_config
            .insert_columns,
            "row_id",
            "version",
            "habilitado",
        )
    def get_connection_status(self) -> bool:
        return self._bigquery.test_connection()

    def get_all_rows(
        self,
    ) -> tuple[dict, ...]:
        table = self._bigquery.get_table(
            self._module_config.main_table
        )

        load_columns = set(
            self.load_columns
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

    def get_rows_by_ids(
        self,
        row_ids,
    ) -> tuple[dict, ...]:
        clean_row_ids = tuple(
            dict.fromkeys(
                str(row_id).strip()
                for row_id in row_ids
                if str(row_id).strip()
            )
        )

        if not clean_row_ids:
            return ()

        table_ref = (
            self._bigquery
            .get_table_reference(
                self._module_config.main_table
            )
        )

        columns = ",\n                ".join(
            f"`{column}`"
            for column in self.load_columns
        )

        query = f"""
            SELECT
                {columns}

            FROM `{table_ref}`

            WHERE
                row_id IN UNNEST(
                    @row_ids
                )
        """

        job_config = (
            bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter(
                        "row_ids",
                        "STRING",
                        list(
                            clean_row_ids
                        ),
                    )
                ]
            )
        )

        result = (
            self._bigquery
            .client
            .query(
                query,
                job_config=job_config,
                location=(
                    self._bigquery
                    .client
                    .location
                    if getattr(
                        self._bigquery.client,
                        "location",
                        None,
                    )
                    else None
                ),
            )
            .result()
        )

        return tuple(
            dict(
                row.items()
            )
            for row in result
        )

    def get_catalog_values(
        self,
        column: str,
        *,
        filters=None,
        limit: int = 500,
    ) -> tuple[str, ...]:
        allowed = set(
            self._module_config
            .dimension_columns
        )

        if column not in allowed:
            raise ValueError(
                "Columna de catalogo "
                f"no valida: {column}"
            )

        if limit < 1:
            raise ValueError(
                "limit debe ser mayor "
                "que cero."
            )

        if limit > 5000:
            raise ValueError(
                "limit no puede superar "
                "5000."
            )

        clean_filters = {}

        for (
            filter_column,
            filter_value,
        ) in dict(
            filters or {}
        ).items():
            if (
                filter_column
                not in allowed
            ):
                raise ValueError(
                    "Filtro de catalogo "
                    "no valido: "
                    f"{filter_column}"
                )

            if (
                filter_column
                == column
            ):
                continue

            if filter_value is None:
                continue

            value = str(
                filter_value
            ).strip()

            if value:
                clean_filters[
                    filter_column
                ] = value

        table_ref = (
            self._bigquery
            .get_table_reference(
                self._module_config
                .main_table
            )
        )

        conditions = [
            "COALESCE(`habilitado`, TRUE)",
            f"`{column}` IS NOT NULL",
            (
                "TRIM(CAST("
                f"`{column}`"
                " AS STRING)) != ''"
            ),
        ]

        parameters = []

        for (
            index,
            (
                filter_column,
                filter_value,
            ),
        ) in enumerate(
            clean_filters.items()
        ):
            parameter_name = (
                f"filter_{index}"
            )

            conditions.append(
                "TRIM(CAST("
                f"`{filter_column}`"
                " AS STRING)) "
                f"= @{parameter_name}"
            )

            parameters.append(
                bigquery
                .ScalarQueryParameter(
                    parameter_name,
                    "STRING",
                    filter_value,
                )
            )

        parameters.append(
            bigquery
            .ScalarQueryParameter(
                "limit",
                "INT64",
                int(limit),
            )
        )

        where_sql = (
            "\n                AND "
            .join(
                conditions
            )
        )

        sql = f"""
            SELECT DISTINCT
                TRIM(
                    CAST(
                        `{column}`
                        AS STRING
                    )
                ) AS value

            FROM `{table_ref}`

            WHERE
                {where_sql}

            ORDER BY value
            LIMIT @limit
        """

        job_config = (
            bigquery
            .QueryJobConfig(
                query_parameters=(
                    parameters
                )
            )
        )

        rows = (
            self._bigquery
            .client
            .query(
                sql,
                job_config=job_config,
                location=(
                    self._bigquery
                    .client
                    .location
                    if getattr(
                        self._bigquery
                        .client,
                        "location",
                        None,
                    )
                    else None
                ),
            )
            .result()
        )

        return tuple(
            str(
                row["value"]
            ).strip()
            for row in rows
            if str(
                row["value"]
                if row["value"]
                is not None
                else ""
            ).strip()
        )

    def get_dimension_snapshot(
        self,
        *,
        enabled_only: bool = True,
    ) -> tuple[dict, ...]:
        columns = (
            *self._module_config
            .dimension_columns,
            "habilitado",
        )

        table_ref = (
            self._bigquery
            .get_table_reference(
                self._module_config
                .main_table
            )
        )

        select_sql = (
            ",\n                "
            .join(
                f"`{column}`"
                for column
                in columns
            )
        )

        where_sql = (
            "\n            WHERE "
            "COALESCE(`habilitado`, TRUE)"
            if enabled_only
            else ""
        )

        sql = f"""
            SELECT
                {select_sql}

            FROM `{table_ref}`
            {where_sql}
        """

        rows = (
            self._bigquery
            .client
            .query(
                sql,
                location=(
                    self._bigquery
                    .client
                    .location
                    if getattr(
                        self._bigquery
                        .client,
                        "location",
                        None,
                    )
                    else None
                ),
            )
            .result()
        )

        return tuple(
            {
                column:
                    values.get(
                        column
                    )
                for column
                in columns
            }
            for values in (
                dict(
                    row.items()
                )
                for row in rows
            )
        )

    def get_page(
        self,
        *,
        limit: int,
        offset: int,
    ) -> PageResult:
        table = self._bigquery.get_table(
            self._module_config.main_table
        )

        app_columns = set(
            self.app_columns
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
            self._module_config
            .groupable_columns
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
            self._bigquery.get_table_reference(
                self._module_config.main_table
            )
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
            for column in (
                self._module_config
                .amount_columns
            )
        )

        sql = f"""
            SELECT
                {group_select},
                COUNT(*) AS registros,
                {usd_select}
            FROM `{table_ref}`
            WHERE COALESCE(`habilitado`, TRUE)
            GROUP BY {group_select}
            ORDER BY `
                {self._module_config.annual_column}
            ` DESC
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
            *self._module_config.amount_columns,
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
