import argparse
import sys

from google.cloud import bigquery

from config import (
    AMOUNT_COLUMNS,
    STRING_COLUMNS,
)


def original_string(column: str) -> str:
    return (
        f"NULLIF(TRIM(CAST(`{column}` AS STRING)), '')"
    )


def clean_string(column: str) -> str:
    return (
        f"NULLIF(TRIM(CAST(`{column}` AS STRING)), '')"
    )


def original_amount(column: str) -> str:
    return f"""
        CASE
            WHEN `{column}` IS NULL
              OR TRIM(CAST(`{column}` AS STRING)) = ''
                THEN NULL

            WHEN TRIM(CAST(`{column}` AS STRING)) = '-'
                THEN NUMERIC '0'

            ELSE SAFE_CAST(
                REPLACE(
                    TRIM(CAST(`{column}` AS STRING)),
                    ',',
                    ''
                )
                AS NUMERIC
            )
        END
    """


def clean_amount(column: str) -> str:
    return f"CAST(`{column}` AS NUMERIC)"


def get_expression(
    column: str,
    is_amount: bool,
    is_original: bool,
) -> str:
    if is_amount:
        if is_original:
            return original_amount(column)

        return clean_amount(column)

    if is_original:
        return original_string(column)

    return clean_string(column)


def compare_column(
    client,
    original_id: str,
    clean_id: str,
    column: str,
    is_amount: bool,
):
    original_expression = get_expression(
        column=column,
        is_amount=is_amount,
        is_original=True,
    )

    clean_expression = get_expression(
        column=column,
        is_amount=is_amount,
        is_original=False,
    )

    sql = f"""
        WITH original_base AS (
            SELECT
                {original_expression} AS value
            FROM `{original_id}`
        ),

        clean_base AS (
            SELECT
                {clean_expression} AS value
            FROM `{clean_id}`
        ),

        original_values AS (
            SELECT
                TO_JSON_STRING(
                    STRUCT(value AS value)
                ) AS value_key,

                ANY_VALUE(
                    CAST(value AS STRING)
                ) AS display_value,

                COUNT(*) AS row_count

            FROM original_base
            GROUP BY value_key
        ),

        clean_values AS (
            SELECT
                TO_JSON_STRING(
                    STRUCT(value AS value)
                ) AS value_key,

                ANY_VALUE(
                    CAST(value AS STRING)
                ) AS display_value,

                COUNT(*) AS row_count

            FROM clean_base
            GROUP BY value_key
        ),

        comparison AS (
            SELECT
                value_key,

                COALESCE(
                    o.display_value,
                    c.display_value,
                    '<NULL>'
                ) AS display_value,

                COALESCE(
                    o.row_count,
                    0
                ) AS original_count,

                COALESCE(
                    c.row_count,
                    0
                ) AS clean_count

            FROM original_values o

            FULL OUTER JOIN clean_values c
                USING (value_key)
        )

        SELECT
            COUNTIF(
                original_count != clean_count
            ) AS different_values,

            COALESCE(
                SUM(
                    ABS(
                        original_count
                        -
                        clean_count
                    )
                ),
                0
            ) AS total_count_difference

        FROM comparison
    """

    row = next(
        client.query(sql).result()
    )

    return (
        int(row["different_values"]),
        int(row["total_count_difference"]),
    )


def show_value_differences(
    client,
    original_id: str,
    clean_id: str,
    column: str,
    is_amount: bool,
    limit: int = 20,
):
    original_expression = get_expression(
        column=column,
        is_amount=is_amount,
        is_original=True,
    )

    clean_expression = get_expression(
        column=column,
        is_amount=is_amount,
        is_original=False,
    )

    sql = f"""
        WITH original_base AS (
            SELECT
                {original_expression} AS value
            FROM `{original_id}`
        ),

        clean_base AS (
            SELECT
                {clean_expression} AS value
            FROM `{clean_id}`
        ),

        original_values AS (
            SELECT
                TO_JSON_STRING(
                    STRUCT(value AS value)
                ) AS value_key,

                ANY_VALUE(
                    CAST(value AS STRING)
                ) AS display_value,

                COUNT(*) AS row_count

            FROM original_base
            GROUP BY value_key
        ),

        clean_values AS (
            SELECT
                TO_JSON_STRING(
                    STRUCT(value AS value)
                ) AS value_key,

                ANY_VALUE(
                    CAST(value AS STRING)
                ) AS display_value,

                COUNT(*) AS row_count

            FROM clean_base
            GROUP BY value_key
        )

        SELECT
            COALESCE(
                o.display_value,
                c.display_value,
                '<NULL>'
            ) AS value,

            COALESCE(
                o.row_count,
                0
            ) AS original_count,

            COALESCE(
                c.row_count,
                0
            ) AS clean_count

        FROM original_values o

        FULL OUTER JOIN clean_values c
            USING (value_key)

        WHERE
            COALESCE(
                o.row_count,
                0
            )
            !=
            COALESCE(
                c.row_count,
                0
            )

        ORDER BY
            ABS(
                COALESCE(
                    o.row_count,
                    0
                )
                -
                COALESCE(
                    c.row_count,
                    0
                )
            ) DESC

        LIMIT {limit}
    """

    return list(
        client.query(sql).result()
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Diagnostica diferencias "
            "entre la tabla original "
            "y la tabla limpia."
        )
    )

    parser.add_argument(
        "--project",
        required=True,
    )

    parser.add_argument(
        "--dataset",
        required=True,
    )

    parser.add_argument(
        "--original",
        required=True,
    )

    parser.add_argument(
        "--clean",
        required=True,
    )

    args = parser.parse_args()

    original_id = (
        f"{args.project}."
        f"{args.dataset}."
        f"{args.original}"
    )

    clean_id = (
        f"{args.project}."
        f"{args.dataset}."
        f"{args.clean}"
    )

    client = bigquery.Client(
        project=args.project
    )

    print()
    print("=" * 100)
    print("DIAGNOSTICO POR COLUMNA")
    print("=" * 100)

    affected_columns = []

    columns_to_check = [
        (column, False)
        for column in STRING_COLUMNS
    ]

    columns_to_check.extend(
        (
            column,
            True,
        )
        for column in AMOUNT_COLUMNS
    )

    for column, is_amount in columns_to_check:
        try:
            (
                different_values,
                total_difference,
            ) = compare_column(
                client=client,
                original_id=original_id,
                clean_id=clean_id,
                column=column,
                is_amount=is_amount,
            )

        except Exception as exc:
            print()
            print(
                f"ERROR EN COLUMNA: {column}"
            )
            print(type(exc).__name__)
            print(str(exc))

            sys.exit(1)

        if different_values == 0:
            continue

        column_type = (
            "NUMERIC"
            if is_amount
            else "STRING"
        )

        affected_columns.append(
            (
                column,
                is_amount,
                different_values,
                total_difference,
            )
        )

        print(
            f"{column:30} "
            f"{column_type:8} "
            f"valores diferentes="
            f"{different_values:>5} "
            f"movimientos="
            f"{total_difference:>5}"
        )

    print()

    if not affected_columns:
        print(
            "No se encontraron diferencias "
            "por columna."
        )
        return

    print("=" * 100)
    print("RESUMEN")
    print("=" * 100)

    print(
        f"Columnas afectadas: "
        f"{len(affected_columns)}"
    )

    print()
    print("=" * 100)
    print("DETALLE DE VALORES DIFERENTES")
    print("=" * 100)

    for (
        column,
        is_amount,
        _,
        _,
    ) in affected_columns:

        print()
        print(
            f"COLUMNA: {column}"
        )

        print("-" * 100)

        rows = show_value_differences(
            client=client,
            original_id=original_id,
            clean_id=clean_id,
            column=column,
            is_amount=is_amount,
        )

        for row in rows:
            print(
                f"Valor={row['value']!r} | "
                f"Original={row['original_count']} | "
                f"Limpia={row['clean_count']}"
            )


if __name__ == "__main__":
    main()