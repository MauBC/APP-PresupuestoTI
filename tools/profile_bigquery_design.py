import argparse
from pathlib import Path

from app.config.presupuesto_app_config import (
    DIMENSION_COLUMNS,
)
from app.config.settings import settings
from app.services.bigquery_service import (
    BigQueryService,
)
from database.bootstrap.schema import (
    STORAGE_BUSINESS_COLUMNS,
)


RELATIONSHIPS = (
    (
        "compania",
        "pais",
    ),
    (
        "ceco",
        "centro_beneficio",
    ),
    (
        "ceco",
        "desc_cebe",
    ),
    (
        "ceco",
        "macroservicio_cg",
    ),
    (
        "ceco",
        "tipo_servicio_cg",
    ),
    (
        "ceco",
        "sede_cg",
    ),
    (
        "ceco",
        "region_cg",
    ),
    (
        "ceco",
        "gyp",
    ),
    (
        "centro_beneficio",
        "desc_cebe",
    ),
    (
        "numero_cuenta",
        "nombre_cuenta",
    ),

    # Relaciones exploratorias.
    # No necesariamente deben ser 1 -> 1.
    (
        "proveedor",
        "categoria_gasto",
    ),
    (
        "categoria_gasto",
        "atributo_2",
    ),
)


class Report:
    def __init__(self):
        self.lines = []
        self.total_bytes_processed = 0

    def add(
        self,
        text="",
    ):
        self.lines.append(
            str(text)
        )

    def title(
        self,
        text,
    ):
        self.add()
        self.add(
            "=" * 100
        )
        self.add(text)
        self.add(
            "=" * 100
        )

    def subtitle(
        self,
        text,
    ):
        self.add()
        self.add(text)
        self.add(
            "-" * 100
        )

    def save(
        self,
        path: Path,
    ):
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            "\n".join(
                self.lines
            )
            + "\n",
            encoding="utf-8",
        )


def quote(
    column,
):
    return (
        "`"
        + column.replace(
            "`",
            "",
        )
        + "`"
    )


def format_bytes(
    value,
):
    if value is None:
        return "-"

    size = float(value)

    units = (
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    )

    for unit in units:
        if size < 1024:
            return (
                f"{size:,.2f} {unit}"
            )

        size /= 1024

    return (
        f"{size:,.2f} PB"
    )


def format_percent(
    numerator,
    denominator,
):
    if not denominator:
        return "0.00%"

    return (
        f"{numerator / denominator * 100:,.2f}%"
    )


def run_query(
    service,
    report,
    sql,
):
    job = service.client.query(
        sql,
        location=settings.BIGQUERY_LOCATION,
    )

    result = job.result()

    report.total_bytes_processed += int(
        job.total_bytes_processed
        or 0
    )

    return [
        dict(
            row.items()
        )
        for row in result
    ]


def build_column_profile_query(
    table_ref,
    schema,
):
    expressions = [
        "COUNT(*) AS total_rows",
    ]

    metadata = []

    for index, field in enumerate(
        schema
    ):
        column = quote(
            field.name
        )

        null_alias = (
            f"c{index}_nulls"
        )

        distinct_alias = (
            f"c{index}_distinct"
        )

        expressions.append(
            "COUNTIF("
            f"{column} IS NULL"
            f") AS {null_alias}"
        )

        expressions.append(
            "COUNT(DISTINCT "
            f"{column}"
            f") AS {distinct_alias}"
        )

        blank_alias = None

        if (
            field.field_type
            == "STRING"
        ):
            blank_alias = (
                f"c{index}_blanks"
            )

            expressions.append(
                "COUNTIF("
                f"{column} IS NOT NULL "
                "AND TRIM("
                f"{column}"
                ") = ''"
                f") AS {blank_alias}"
            )

        metadata.append(
            (
                field,
                null_alias,
                distinct_alias,
                blank_alias,
            )
        )

    sql = (
        "SELECT\n    "
        + ",\n    ".join(
            expressions
        )
        + "\n"
        + f"FROM `{table_ref}`"
    )

    return (
        sql,
        metadata,
    )


def profile_columns(
    service,
    report,
    table_ref,
    schema,
):
    report.title(
        "3. PERFIL DE COLUMNAS"
    )

    sql, metadata = (
        build_column_profile_query(
            table_ref,
            schema,
        )
    )

    rows = run_query(
        service,
        report,
        sql,
    )

    result = rows[0]

    total_rows = int(
        result[
            "total_rows"
        ]
    )

    report.add(
        "COLUMN"
        " | TYPE"
        " | MODE"
        " | NULL"
        " | NULL %"
        " | DISTINCT"
        " | REPETITION %"
        " | BLANK"
    )

    report.add(
        "-" * 100
    )

    profile = {}

    for (
        field,
        null_alias,
        distinct_alias,
        blank_alias,
    ) in metadata:
        null_count = int(
            result[
                null_alias
            ]
            or 0
        )

        distinct_count = int(
            result[
                distinct_alias
            ]
            or 0
        )

        blank_count = (
            int(
                result[
                    blank_alias
                ]
                or 0
            )
            if blank_alias
            else 0
        )

        non_null = (
            total_rows
            - null_count
        )

        repeated = max(
            non_null
            - distinct_count,
            0,
        )

        repetition_percent = (
            repeated
            / non_null
            * 100
            if non_null
            else 0.0
        )

        profile[
            field.name
        ] = {
            "null_count": (
                null_count
            ),
            "distinct_count": (
                distinct_count
            ),
            "blank_count": (
                blank_count
            ),
            "non_null": (
                non_null
            ),
            "repetition_percent": (
                repetition_percent
            ),
        }

        report.add(
            f"{field.name}"
            f" | {field.field_type}"
            f" | {field.mode}"
            f" | {null_count:,}"
            f" | {format_percent(null_count, total_rows)}"
            f" | {distinct_count:,}"
            f" | {repetition_percent:,.2f}%"
            f" | {blank_count:,}"
        )

    return (
        total_rows,
        profile,
    )


def technical_checks(
    service,
    report,
    table_ref,
):
    report.title(
        "2. VALIDACIONES TECNICAS"
    )

    sql = f"""
        SELECT
            COUNT(*) AS total_rows,

            COUNT(DISTINCT row_id)
                AS unique_row_ids,

            COUNTIF(
                row_id IS NULL
                OR TRIM(row_id) = ''
            ) AS missing_row_ids,

            COUNTIF(
                habilitado IS NULL
            ) AS null_habilitado,

            COUNTIF(
                habilitado = FALSE
            ) AS disabled_rows,

            COUNTIF(
                version IS NULL
            ) AS null_versions,

            MIN(version)
                AS min_version,

            MAX(version)
                AS max_version

        FROM `{table_ref}`
    """

    row = run_query(
        service,
        report,
        sql,
    )[0]

    for key, value in (
        row.items()
    ):
        if isinstance(
            value,
            int,
        ):
            value = (
                f"{value:,}"
            )

        report.add(
            f"{key:25}: {value}"
        )


def duplicate_checks(
    service,
    report,
    table_ref,
):
    report.title(
        "5. DUPLICADOS Y GRANULARIDAD"
    )

    business_columns = ",\n                ".join(
        quote(column)
        for column
        in STORAGE_BUSINESS_COLUMNS
    )

    sql = f"""
        WITH grouped_rows AS (
            SELECT
                {business_columns},
                COUNT(*) AS records
            FROM `{table_ref}`
            GROUP BY
                {business_columns}
        )

        SELECT
            COUNT(*) AS distinct_business_rows,
            COUNTIF(records > 1)
                AS duplicate_groups,
            COALESCE(
                SUM(
                    IF(
                        records > 1,
                        records - 1,
                        0
                    )
                ),
                0
            ) AS extra_duplicate_rows,
            COALESCE(
                MAX(records),
                0
            ) AS largest_duplicate_group
        FROM grouped_rows
    """

    row = run_query(
        service,
        report,
        sql,
    )[0]

    report.subtitle(
        "5.1 Duplicados exactos de las 60 columnas de negocio"
    )

    for key, value in (
        row.items()
    ):
        report.add(
            f"{key:30}: "
            f"{int(value or 0):,}"
        )

    dimension_columns = ",\n                ".join(
        quote(column)
        for column
        in DIMENSION_COLUMNS
    )

    sql = f"""
        WITH grouped_rows AS (
            SELECT
                {dimension_columns},
                COUNT(*) AS records
            FROM `{table_ref}`
            GROUP BY
                {dimension_columns}
        )

        SELECT
            COUNT(*) AS distinct_dimension_combinations,
            COUNTIF(records > 1)
                AS repeated_dimension_groups,
            COALESCE(
                SUM(
                    IF(
                        records > 1,
                        records - 1,
                        0
                    )
                ),
                0
            ) AS rows_beyond_first,
            COALESCE(
                MAX(records),
                0
            ) AS largest_dimension_group
        FROM grouped_rows
    """

    row = run_query(
        service,
        report,
        sql,
    )[0]

    report.subtitle(
        "5.2 Repeticion usando solamente las 21 dimensiones"
    )

    for key, value in (
        row.items()
    ):
        report.add(
            f"{key:35}: "
            f"{int(value or 0):,}"
        )


def dimension_summary(
    report,
    total_rows,
    profile,
):
    report.title(
        "4. CARDINALIDAD DE DIMENSIONES"
    )

    report.add(
        "DIMENSION"
        " | DISTINCT"
        " | NON NULL"
        " | AVG ROWS / VALUE"
        " | REPETITION %"
    )

    report.add(
        "-" * 100
    )

    for column in (
        DIMENSION_COLUMNS
    ):
        values = profile.get(
            column
        )

        if values is None:
            continue

        distinct_count = (
            values[
                "distinct_count"
            ]
        )

        non_null = (
            values[
                "non_null"
            ]
        )

        avg_rows = (
            non_null
            / distinct_count
            if distinct_count
            else 0
        )

        report.add(
            f"{column}"
            f" | {distinct_count:,}"
            f" | {non_null:,}"
            f" | {avg_rows:,.2f}"
            f" | "
            f"{values['repetition_percent']:,.2f}%"
        )


def relationship_checks(
    service,
    report,
    table_ref,
    available_columns,
):
    report.title(
        "6. RELACIONES FUNCIONALES / CANDIDATOS A DIMENSION"
    )

    valid_relationships = [
        pair
        for pair in RELATIONSHIPS
        if (
            pair[0]
            in available_columns
            and pair[1]
            in available_columns
        )
    ]

    structs = []

    for (
        determinant,
        dependent,
    ) in valid_relationships:
        relation = (
            f"{determinant} -> "
            f"{dependent}"
        )

        structs.append(
            "STRUCT("
            f"'{relation}' AS relation, "
            f"CAST({quote(determinant)} AS STRING) "
            "AS determinant, "
            f"CAST({quote(dependent)} AS STRING) "
            "AS dependent"
            ")"
        )

    if not structs:
        report.add(
            "No existen relaciones disponibles."
        )
        return

    struct_sql = ",\n                ".join(
        structs
    )

    base_cte = f"""
        WITH expanded AS (
            SELECT
                pair.relation,
                pair.determinant,
                pair.dependent
            FROM `{table_ref}`,
            UNNEST([
                {struct_sql}
            ]) AS pair
            WHERE
                pair.determinant IS NOT NULL
                AND TRIM(
                    pair.determinant
                ) != ''
        ),

        per_key AS (
            SELECT
                relation,
                determinant,
                COUNT(
                    DISTINCT COALESCE(
                        dependent,
                        '__NULL__'
                    )
                ) AS dependent_values
            FROM expanded
            GROUP BY
                relation,
                determinant
        )
    """

    summary_sql = (
        base_cte
        + """
        SELECT
            relation,
            COUNT(*) AS determinant_keys,
            COUNTIF(
                dependent_values > 1
            ) AS violating_keys,
            MAX(
                dependent_values
            ) AS max_dependent_values
        FROM per_key
        GROUP BY relation
        ORDER BY relation
        """
    )

    rows = run_query(
        service,
        report,
        summary_sql,
    )

    report.add(
        "RELATION"
        " | KEYS"
        " | VIOLATIONS"
        " | MAX VALUES / KEY"
        " | RESULT"
    )

    report.add(
        "-" * 100
    )

    has_violations = False

    for row in rows:
        violations = int(
            row[
                "violating_keys"
            ]
            or 0
        )

        has_violations = (
            has_violations
            or violations > 0
        )

        result = (
            "STRICT 1->1"
            if violations == 0
            else "NOT STRICT"
        )

        report.add(
            f"{row['relation']}"
            f" | {int(row['determinant_keys']):,}"
            f" | {violations:,}"
            f" | {int(row['max_dependent_values'] or 0):,}"
            f" | {result}"
        )

    if not has_violations:
        return

    example_sql = (
        base_cte
        + """
        SELECT
            relation,
            determinant,
            dependent_values
        FROM per_key
        WHERE
            dependent_values > 1
        QUALIFY
            ROW_NUMBER() OVER (
                PARTITION BY relation
                ORDER BY
                    dependent_values DESC,
                    determinant
            ) <= 3
        ORDER BY
            relation,
            dependent_values DESC
        """
    )

    examples = run_query(
        service,
        report,
        example_sql,
    )

    if not examples:
        return

    report.subtitle(
        "Ejemplos limitados de claves con multiples valores"
    )

    for row in examples:
        report.add(
            f"{row['relation']}"
            f" | key={row['determinant']!r}"
            f" | distinct_dependents="
            f"{int(row['dependent_values']):,}"
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Perfil de solo lectura para "
            "evaluar el diseno de presupuesto_2026."
        )
    )

    parser.add_argument(
        "--output",
        default=(
            "data_local/"
            "bigquery_design_profile.txt"
        ),
        help=(
            "Ruta del TXT de salida."
        ),
    )

    args = parser.parse_args()

    output_path = (
        Path(args.output)
        .expanduser()
        .resolve()
    )

    service = (
        BigQueryService()
    )

    table_ref = (
        service
        .get_table_reference()
    )

    table = (
        service.get_table()
    )

    report = Report()

    report.title(
        "BIGQUERY DESIGN PROFILE"
    )

    report.add(
        "MODO: SOLO LECTURA"
    )

    report.add(
        "No se ejecutan INSERT, UPDATE, "
        "DELETE, MERGE, CREATE ni DROP."
    )

    report.title(
        "1. INFORMACION DE LA TABLA"
    )

    report.add(
        f"Tabla                   : "
        f"{table_ref}"
    )

    report.add(
        f"Location                : "
        f"{table.location}"
    )

    report.add(
        f"Filas metadata          : "
        f"{table.num_rows:,}"
    )

    report.add(
        f"Columnas                : "
        f"{len(table.schema):,}"
    )

    report.add(
        f"Tamano logico           : "
        f"{format_bytes(table.num_bytes)}"
    )

    report.add(
        "Particionamiento        : "
        + (
            str(
                table.time_partitioning
            )
            if table.time_partitioning
            else "NO"
        )
    )

    report.add(
        "Clustering              : "
        + (
            ", ".join(
                table.clustering_fields
            )
            if table.clustering_fields
            else "NO"
        )
    )

    report.subtitle(
        "Esquema"
    )

    for index, field in enumerate(
        table.schema,
        start=1,
    ):
        report.add(
            f"{index:02}. "
            f"{field.name:30}"
            f" | {field.field_type:12}"
            f" | {field.mode}"
        )

    technical_checks(
        service,
        report,
        table_ref,
    )

    (
        total_rows,
        profile,
    ) = profile_columns(
        service,
        report,
        table_ref,
        table.schema,
    )

    dimension_summary(
        report,
        total_rows,
        profile,
    )

    duplicate_checks(
        service,
        report,
        table_ref,
    )

    relationship_checks(
        service,
        report,
        table_ref,
        {
            field.name
            for field in table.schema
        },
    )

    report.title(
        "7. COSTO DE LA INSPECCION"
    )

    report.add(
        "Bytes procesados reportados "
        "por los query jobs:"
    )

    report.add(
        format_bytes(
            report.total_bytes_processed
        )
    )

    report.add()
    report.add(
        "Este reporte contiene estadisticas "
        "agregadas; no exporta la tabla completa."
    )

    report.save(
        output_path
    )

    print()
    print(
        "Perfil generado correctamente."
    )

    print(
        f"Archivo: {output_path}"
    )

    print(
        "Tamano: "
        f"{format_bytes(output_path.stat().st_size)}"
    )

    print()


if __name__ == "__main__":
    main()

