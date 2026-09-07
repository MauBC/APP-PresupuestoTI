import argparse

from google.cloud import bigquery

from app.config.settings import settings
from database.bootstrap.bigquery_contract import (
    build_bootstrap_load_config,
)
from database.bootstrap.pipeline import (
    prepare_budget,
)


def main():
    parser = argparse.ArgumentParser(
        description="Carga inicial del presupuesto a BigQuery."
    )

    parser.add_argument(
        "--file",
        required=True,
    )

    parser.add_argument(
        "--actor",
        required=True,
    )

    parser.add_argument(
        "--sheet",
        default="0",
    )

    args = parser.parse_args()

    sheet = (
        int(args.sheet)
        if args.sheet.isdigit()
        else args.sheet
    )

    print()
    print("Preparando archivo...")

    preparation = prepare_budget(
        args.file,
        actor=args.actor,
        sheet_name=sheet,
    )

    project = settings.GOOGLE_CLOUD_PROJECT
    dataset = settings.BIGQUERY_DATASET
    table = settings.BIGQUERY_TABLE
    location = settings.BIGQUERY_LOCATION

    table_id = (
        f"{project}."
        f"{dataset}."
        f"{table}"
    )

    print()
    print("=" * 70)
    print("BOOTSTRAP BIGQUERY")
    print("=" * 70)
    print(f"Proyecto : {project}")
    print(f"Dataset  : {dataset}")
    print(f"Tabla    : {table}")
    print(f"Location : {location}")
    print(
        f"Filas    : "
        f"{preparation.final_row_count:,}"
    )
    print(
        f"Columnas : "
        f"{preparation.final_column_count}"
    )

    client = bigquery.Client(
        project=project,
        location=location,
    )

    dataset_id = (
        f"{project}.{dataset}"
    )

    client.get_dataset(
        dataset_id
    )

    job_config = (
        build_bootstrap_load_config()
    )

    print()
    print("Cargando datos a BigQuery...")

    load_job = (
        client.load_table_from_dataframe(
            preparation.dataframe,
            table_id,
            job_config=job_config,
            location=location,
        )
    )

    load_job.result()

    print("Carga terminada.")
    print()
    print("Validando tabla...")

    query = f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT row_id) AS unique_row_ids,
            COUNTIF(habilitado = FALSE) AS disabled_rows,
            MIN(version) AS min_version,
            MAX(version) AS max_version
        FROM `{table_id}`
    """

    row = next(
        iter(
            client.query(
                query,
                location=location,
            ).result()
        )
    )

    total_rows = int(
        row.total_rows
    )

    unique_row_ids = int(
        row.unique_row_ids
    )

    disabled_rows = int(
        row.disabled_rows
    )

    min_version = int(
        row.min_version
    )

    max_version = int(
        row.max_version
    )

    expected_rows = (
        preparation.final_row_count
    )

    if total_rows != expected_rows:
        raise RuntimeError(
            "Cantidad de filas incorrecta: "
            f"{total_rows} != {expected_rows}"
        )

    if unique_row_ids != expected_rows:
        raise RuntimeError(
            "Los row_id no son unicos."
        )

    if disabled_rows != 0:
        raise RuntimeError(
            "Existen filas deshabilitadas "
            "en la carga inicial."
        )

    if (
        min_version != 1
        or max_version != 1
    ):
        raise RuntimeError(
            "La version inicial "
            "debe ser 1."
        )

    table_info = (
        client.get_table(
            table_id
        )
    )

    print()
    print("=" * 70)
    print("BOOTSTRAP COMPLETADO")
    print("=" * 70)

    print(
        f"Tabla              : "
        f"{table_id}"
    )

    print(
        f"Filas BigQuery     : "
        f"{total_rows:,}"
    )

    print(
        f"Columnas BigQuery  : "
        f"{len(table_info.schema)}"
    )

    print(
        f"row_id unicos      : "
        f"{unique_row_ids:,}"
    )

    print(
        f"Deshabilitados     : "
        f"{disabled_rows}"
    )

    print(
        f"Version minima     : "
        f"{min_version}"
    )

    print(
        f"Version maxima     : "
        f"{max_version}"
    )

    print()
    print("RESULTADO           : OK")
    print()


if __name__ == "__main__":
    main()