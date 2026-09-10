
from decimal import Decimal

from app.config.settings import (
    settings,
)


ZERO = Decimal("0")


class BudgetSummaryRepositoryError(
    RuntimeError
):
    pass


class BudgetSummaryRepository:
    def __init__(
        self,
        bigquery_service,
        *,
        module_config,
    ):
        self._bigquery = (
            bigquery_service
        )

        self._config = (
            module_config
        )

    @property
    def module_config(
        self,
    ):
        return self._config

    def get_summary_rows(
        self,
        definition,
    ) -> tuple[
        dict,
        ...
    ]:
        self._validate_definition(
            definition
        )

        table_ref = (
            self._bigquery
            .get_table_reference(
                self._config
                .main_table
            )
        )

        source_dimensions = ",\n                ".join(
            self._source_dimension_expression(
                column
            )
            for column
            in definition.group_by
        )

        selected_dimensions = ",\n                ".join(
            f"`{column}`"
            for column
            in definition.group_by
        )

        group_dimensions = ", ".join(
            f"`{column}`"
            for column
            in definition.group_by
        )

        order_dimensions = ", ".join(
            f"`{column}`"
            for column
            in definition.group_by
        )

        sql = f"""
            WITH source AS (
                SELECT
                    {source_dimensions},
                    COALESCE(
                        `{definition.amount_column}`,
                        NUMERIC '0'
                    ) AS `_summary_amount`

                FROM `{table_ref}`

                WHERE
                    COALESCE(
                        `habilitado`,
                        TRUE
                    )
            ),

            grouped AS (
                SELECT
                    {selected_dimensions},
                    COUNT(*) AS registros_origen,
                    COALESCE(
                        SUM(
                            `_summary_amount`
                        ),
                        NUMERIC '0'
                    ) AS total_usd

                FROM source

                GROUP BY
                    {group_dimensions}
            )

            SELECT
                {selected_dimensions},
                registros_origen,
                total_usd,

                SUM(
                    registros_origen
                ) OVER () AS `_source_row_count`,

                SUM(
                    total_usd
                ) OVER () AS `_source_total_usd`

            FROM grouped

            ORDER BY
                total_usd DESC,
                {order_dimensions}
        """

        rows = (
            self._bigquery
            .client
            .query(
                sql,
                location=(
                    settings
                    .BIGQUERY_LOCATION
                    or None
                ),
            )
            .result()
        )

        return tuple(
            dict(
                row.items()
            )
            if hasattr(
                row,
                "items",
            )
            else dict(row)
            for row in rows
        )

    def _validate_definition(
        self,
        definition,
    ):
        if (
            str(
                definition.module
            ).strip().upper()
            !=
            self._config
            .module
            .value
        ):
            raise (
                BudgetSummaryRepositoryError(
                    "El resumen no pertenece "
                    "al modulo activo."
                )
            )

        allowed_dimensions = set(
            self._config
            .dimension_columns
        )

        invalid_dimensions = tuple(
            column
            for column
            in definition.group_by
            if column
            not in allowed_dimensions
        )

        if invalid_dimensions:
            raise (
                BudgetSummaryRepositoryError(
                    "El resumen contiene "
                    "dimensiones invalidas: "
                    + ", ".join(
                        invalid_dimensions
                    )
                )
            )

        if (
            definition.amount_column
            not in
            self._config.amount_columns
        ):
            raise (
                BudgetSummaryRepositoryError(
                    "La columna financiera "
                    "del resumen no pertenece "
                    "al contrato editable "
                    "del modulo."
                )
            )

    def _source_dimension_expression(
        self,
        column,
    ):
        value_type = (
            self._config
            .insert_type_map
            .get(
                column,
                "STRING",
            )
        )

        if (
            str(value_type)
            .strip()
            .upper()
            == "STRING"
        ):
            return (
                "NULLIF("
                "TRIM("
                "CAST("
                f"`{column}` "
                "AS STRING"
                ")"
                "), "
                "''"
                ") "
                f"AS `{column}`"
            )

        return (
            f"`{column}`"
        )
