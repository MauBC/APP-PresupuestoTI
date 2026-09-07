import argparse
import sys

from google.cloud import bigquery

from config import (
    AMOUNT_COLUMNS,
    STRING_COLUMNS,
)


def normalize_string(column: str) -> str:
    return (
        f"NULLIF(TRIM(CAST(`{column}` AS STRING)), '')"
    )


def normalize_original_amount(column: str) -> str:
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


def normalize_clean_amount(column: str) -> str:
    return f"CAST(`{column}` AS NUMERIC)"


def build_struct(
    is_original: bool,
) -> str:
    expressions = []

    for column in STRING_COLUMNS:
        expressions.append(
            f"{normalize_string(column)} AS `{column}`"
        )

    for column in AMOUNT_COLUMNS:
        if is_original:
            expression = normalize_original_amount(
                column
            )
        else:
            expression = normalize_clean_amount(
                column
            )

        expressions.append(
            f"{expression} AS `{column}`"
        )

    return ",\n".join(expressions)


def check_schema(
    client,
    original_id: str,
    clean_id: str,
):
    original = client.get_table(original_id)
    clean = client.get_table(clean_id)

    print()
    print("=" * 90)
    print("ESQUEMA")
    print("=" * 90)

    print(
        f"Original: {original.num_rows:,} filas / "
        f"{len(original.schema)} columnas"
    )

    print(
        f"Limpia  : {clean.num_rows:,} filas / "
        f"{len(clean.schema)} columnas"
    )

    clean_types = {
        field.name: field.field_type
        for field in clean.schema
    }

    string_errors = [
        column
        for column in STRING_COLUMNS
        if clean_types.get(column) != "STRING"
    ]

    numeric_errors = [
        column
        for column in AMOUNT_COLUMNS
        if clean_types.get(column) != "NUMERIC"
    ]

    if string_errors:
        print()
        print("ERROR: columnas que deberian ser STRING:")
        for column in string_errors:
            print(f"  - {column}: {clean_types.get(column)}")

    if numeric_errors:
        print()
        print("ERROR: columnas que deberian ser NUMERIC:")
        for column in numeric_errors:
            print(f"  - {column}: {clean_types.get(column)}")

    schema_ok = (
        not string_errors
        and not numeric_errors
        and len(clean.schema)
        == len(STRING_COLUMNS) + len(AMOUNT_COLUMNS)
    )

    print()
    print(
        "Esquema limpio: "
        + ("OK" if schema_ok else "ERROR")
    )

    return (
        original.num_rows,
        clean.num_rows,
        schema_ok,
    )


def compare_data(
    client,
    original_id: str,
    clean_id: str,
):
    original_struct = build_struct(
        is_original=True
    )

    clean_struct = build_struct(
        is_original=False
    )

    sql = f"""
        WITH original_normalized AS (
            SELECT
                TO_JSON_STRING(
                    STRUCT(
                        {original_struct}
                    )
                ) AS row_key
            FROM `{original_id}`
        ),

        clean_normalized AS (
            SELECT
                TO_JSON_STRING(
                    STRUCT(
                        {clean_struct}
                    )
                ) AS row_key
            FROM `{clean_id}`
        ),

        original_counts AS (
            SELECT
                row_key,
                COUNT(*) AS row_count
            FROM original_normalized
            GROUP BY row_key
        ),

        clean_counts AS (
            SELECT
                row_key,
                COUNT(*) AS row_count
            FROM clean_normalized
            GROUP BY row_key
        ),

        comparison AS (
            SELECT
                COALESCE(
                    o.row_key,
                    c.row_key
                ) AS row_key,

                COALESCE(
                    o.row_count,
                    0
                ) AS original_count,

                COALESCE(
                    c.row_count,
                    0
                ) AS clean_count

            FROM original_counts o

            FULL OUTER JOIN clean_counts c
                USING (row_key)
        )

        SELECT
            COUNTIF(
                original_count != clean_count
            ) AS different_groups,

            COALESCE(
                SUM(
                    GREATEST(
                        original_count - clean_count,
                        0
                    )
                ),
                0
            ) AS missing_in_clean,

            COALESCE(
                SUM(
                    GREATEST(
                        clean_count - original_count,
                        0
                    )
                ),
                0
            ) AS extra_in_clean

        FROM comparison
    """

    row = next(
        client.query(sql).result()
    )

    print()
    print("=" * 90)
    print("COMPARACION DE DATOS")
    print("=" * 90)

    print(
        f"Grupos diferentes     : "
        f"{row['different_groups']:,}"
    )

    print(
        f"Filas faltantes limpia: "
        f"{row['missing_in_clean']:,}"
    )

    print(
        f"Filas extra limpia    : "
        f"{row['extra_in_clean']:,}"
    )

    return (
        row["different_groups"] == 0
        and row["missing_in_clean"] == 0
        and row["extra_in_clean"] == 0
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Compara la tabla original con "
            "la tabla limpia de presupuesto."
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

    client = bigquery.Client(
        project=args.project
    )

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

    try:
        (
            original_rows,
            clean_rows,
            schema_ok,
        ) = check_schema(
            client,
            original_id,
            clean_id,
        )

        data_ok = compare_data(
            client,
            original_id,
            clean_id,
        )

    except Exception as exc:
        print()
        print("ERROR DURANTE LA COMPARACION")
        print(type(exc).__name__)
        print(str(exc))
        sys.exit(1)

    rows_ok = (
        original_rows == clean_rows
    )

    print()
    print("=" * 90)
    print("RESULTADO FINAL")
    print("=" * 90)

    print(
        f"Misma cantidad de filas : "
        f"{'OK' if rows_ok else 'ERROR'}"
    )

    print(
        f"Esquema correcto        : "
        f"{'OK' if schema_ok else 'ERROR'}"
    )

    print(
        f"Datos equivalentes      : "
        f"{'OK' if data_ok else 'ERROR'}"
    )

    if (
        rows_ok
        and schema_ok
        and data_ok
    ):
        print()
        print(
            "TABLA LIMPIA VALIDADA CORRECTAMENTE"
        )

        sys.exit(0)

    print()
    print(
        "LA TABLA REQUIERE REVISION"
    )

    sys.exit(2)


if __name__ == "__main__":
    main()