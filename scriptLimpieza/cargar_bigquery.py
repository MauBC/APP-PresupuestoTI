import argparse
import sys
from pathlib import Path

from google.cloud import bigquery

from config import (
    AMOUNT_COLUMNS,
    STRING_COLUMNS,
)


def build_schema():
    schema = []

    for column in STRING_COLUMNS:
        schema.append(
            bigquery.SchemaField(
                column,
                "STRING",
                mode="NULLABLE",
            )
        )

    for column in AMOUNT_COLUMNS:
        schema.append(
            bigquery.SchemaField(
                column,
                "NUMERIC",
                mode="NULLABLE",
            )
        )

    return schema


def load_csv(
    file_path: Path,
    project: str,
    dataset: str,
    table: str,
):
    client = bigquery.Client(
        project=project
    )

    table_id = (
        f"{project}.{dataset}.{table}"
    )

    schema = build_schema()

    job_config = (
        bigquery.LoadJobConfig()
    )

    job_config.schema = schema
    job_config.source_format = (
        bigquery.SourceFormat.CSV
    )

    job_config.skip_leading_rows = 1
    job_config.autodetect = False

    job_config.write_disposition = (
        bigquery.WriteDisposition.WRITE_TRUNCATE
    )

    job_config.allow_quoted_newlines = True

    print()
    print("=" * 80)
    print("CARGA BIGQUERY")
    print("=" * 80)

    print()
    print(f"Archivo : {file_path}")
    print(f"Proyecto: {project}")
    print(f"Dataset : {dataset}")
    print(f"Tabla   : {table}")

    print()
    print(
        f"Columnas STRING : "
        f"{len(STRING_COLUMNS)}"
    )

    print(
        f"Columnas NUMERIC: "
        f"{len(AMOUNT_COLUMNS)}"
    )

    print()
    print("Iniciando carga...")

    with file_path.open("rb") as file:
        load_job = (
            client.load_table_from_file(
                file,
                table_id,
                job_config=job_config,
            )
        )

        load_job.result()

    table_obj = client.get_table(
        table_id
    )

    print()
    print("=" * 80)
    print("CARGA COMPLETADA")
    print("=" * 80)

    print(
        f"Filas cargadas  : "
        f"{table_obj.num_rows:,}"
    )

    print(
        f"Columnas        : "
        f"{len(table_obj.schema)}"
    )

    print()
    print("TIPOS:")

    string_count = sum(
        1
        for field in table_obj.schema
        if field.field_type == "STRING"
    )

    numeric_count = sum(
        1
        for field in table_obj.schema
        if field.field_type == "NUMERIC"
    )

    print(
        f"STRING : {string_count}"
    )

    print(
        f"NUMERIC: {numeric_count}"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Carga un presupuesto limpio "
            "a BigQuery con esquema explicito."
        )
    )

    parser.add_argument(
        "archivo",
        help="CSV limpio a cargar.",
    )

    parser.add_argument(
        "--project",
        required=True,
        help="Google Cloud Project ID.",
    )

    parser.add_argument(
        "--dataset",
        required=True,
        help="Dataset BigQuery.",
    )

    parser.add_argument(
        "--table",
        required=True,
        help="Tabla destino.",
    )

    args = parser.parse_args()

    file_path = Path(
        args.archivo
    ).expanduser().resolve()

    if not file_path.exists():
        print(
            f"ERROR: no existe el archivo: "
            f"{file_path}"
        )

        sys.exit(1)

    try:
        load_csv(
            file_path=file_path,
            project=args.project,
            dataset=args.dataset,
            table=args.table,
        )

    except Exception as exc:
        print()
        print("ERROR DURANTE LA CARGA")
        print(type(exc).__name__)
        print(str(exc))

        sys.exit(1)


if __name__ == "__main__":
    main()