from app.config.presupuesto_app_config import (
    USD_MONTH_COLUMNS,
)
from app.services.bigquery_service import (
    BigQueryService,
)


def main():
    service = BigQueryService()

    table_ref = (
        service.get_table_reference()
    )

    months_sum = " + ".join(
        (
            "COALESCE("
            f"`{column}`, "
            "NUMERIC '0'"
            ")"
        )
        for column in USD_MONTH_COLUMNS
    )

    negative_condition = " OR ".join(
        f"`{column}` < 0"
        for column in USD_MONTH_COLUMNS
    )

    sql = f"""
        WITH base AS (
            SELECT
                *,
                ({months_sum}) AS calculated_total
            FROM `{table_ref}`
        )

        SELECT
            COUNT(*) AS total_rows,

            COUNTIF(
                ABS(
                    COALESCE(
                        `anio_usd`,
                        NUMERIC '0'
                    )
                    - calculated_total
                ) > NUMERIC '0.01'
            ) AS annual_mismatch_over_cent,

            COUNTIF(
                ABS(
                    COALESCE(
                        `anio_usd`,
                        NUMERIC '0'
                    )
                    - calculated_total
                ) > NUMERIC '1'
            ) AS annual_mismatch_over_one,

            COUNTIF(
                COALESCE(
                    `anio_usd`,
                    NUMERIC '0'
                ) = 0
            ) AS annual_zero,

            COUNTIF(
                calculated_total = 0
            ) AS months_sum_zero,

            COUNTIF(
                (
                    COALESCE(
                        `anio_usd`,
                        NUMERIC '0'
                    ) = 0
                )
                AND
                calculated_total != 0
            ) AS annual_zero_but_months_nonzero,

            COUNTIF(
                {negative_condition}
            ) AS rows_with_negative_month,

            COUNTIF(
                `anio_usd` < 0
            ) AS rows_with_negative_annual,

            MAX(
                ABS(
                    COALESCE(
                        `anio_usd`,
                        NUMERIC '0'
                    )
                    - calculated_total
                )
            ) AS max_annual_difference

        FROM base
    """

    row = next(
        service.client.query(sql).result()
    )

    print("=" * 80)
    print("DIAGNOSTICO USD")
    print("=" * 80)

    print(
        f"Filas totales                    : "
        f"{row['total_rows']:,}"
    )

    print(
        f"Diferencia anual > 0.01 USD      : "
        f"{row['annual_mismatch_over_cent']:,}"
    )

    print(
        f"Diferencia anual > 1 USD         : "
        f"{row['annual_mismatch_over_one']:,}"
    )

    print(
        f"ANIO_USD = 0                     : "
        f"{row['annual_zero']:,}"
    )

    print(
        f"Suma de meses = 0                : "
        f"{row['months_sum_zero']:,}"
    )

    print(
        f"ANIO=0 pero meses != 0           : "
        f"{row['annual_zero_but_months_nonzero']:,}"
    )

    print(
        f"Filas con algun mes negativo     : "
        f"{row['rows_with_negative_month']:,}"
    )

    print(
        f"Filas con ANIO_USD negativo      : "
        f"{row['rows_with_negative_annual']:,}"
    )

    print(
        f"Mayor diferencia anual encontrada: "
        f"{row['max_annual_difference']}"
    )

    print("=" * 80)


if __name__ == "__main__":
    main()