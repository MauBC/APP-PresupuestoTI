import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT_DIR),
    )


from app.services.bigquery_service import BigQueryService


def print_separator():
    print("-" * 100)


def inspect_table(sample_rows: int):
    service = BigQueryService()

    table = service.get_table()

    print()
    print("=" * 100)
    print("BIGQUERY TABLE INSPECTOR")
    print("=" * 100)

    print(f"Proyecto : {table.project}")
    print(f"Dataset  : {table.dataset_id}")
    print(f"Tabla    : {table.table_id}")
    print(f"Filas    : {table.num_rows:,}")
    print(f"Columnas : {len(table.schema)}")

    if table.location:
        print(f"Region   : {table.location}")

    print()
    print("ESQUEMA")
    print_separator()

    print(
        f"{'COLUMNA':35}"
        f"{'TIPO':20}"
        f"{'MODO':15}"
        f"DESCRIPCION"
    )

    print_separator()

    for field in table.schema:
        print(
            f"{field.name:35}"
            f"{field.field_type:20}"
            f"{field.mode:15}"
            f"{field.description or ''}"
        )

    if sample_rows <= 0:
        return

    print()
    print(
        f"MUESTRA DE DATOS ({sample_rows} registros)"
    )
    print_separator()

    rows = service.get_sample_rows(
        sample_rows
    )

    if not rows:
        print("La tabla no contiene registros.")
        return

    for index, row in enumerate(
        rows,
        start=1,
    ):
        print()
        print(f"REGISTRO {index}")
        print(
            json.dumps(
                row,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Inspeccion de solo lectura "
            "de la tabla configurada en BigQuery."
        )
    )

    parser.add_argument(
        "--rows",
        type=int,
        default=5,
        help=(
            "Cantidad de registros de muestra. "
            "Usar 0 para mostrar solo el esquema."
        ),
    )

    args = parser.parse_args()

    try:
        inspect_table(
            sample_rows=args.rows
        )
    except Exception as exc:
        print()
        print("ERROR AL INSPECCIONAR BIGQUERY")
        print(type(exc).__name__)
        print(str(exc))

        sys.exit(1)


if __name__ == "__main__":
    main()
