import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from config import (
    AMOUNT_COLUMNS,
    EXPECTED_COLUMNS,
    STRING_COLUMNS,
)


class CleaningError(Exception):
    pass


def load_csv(file_path: Path) -> pd.DataFrame:
    encodings = (
        "utf-8-sig",
        "utf-8",
        "latin-1",
    )

    last_error = None

    for encoding in encodings:
        try:
            return pd.read_csv(
                file_path,
                dtype=object,
                encoding=encoding,
                low_memory=False,
                keep_default_na=False,
            )
        except UnicodeDecodeError as exc:
            last_error = exc

    raise CleaningError(
        "No se pudo detectar la codificacion del CSV."
    ) from last_error


def load_file(
    file_path: Path,
    sheet_name=0,
) -> pd.DataFrame:
    extension = file_path.suffix.lower()

    if extension == ".csv":
        return load_csv(file_path)

    if extension in {".xlsx", ".xlsm"}:
        return pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            dtype=object,
            keep_default_na=False,
        )

    if extension == ".json":
        with file_path.open(
            "r",
            encoding="utf-8-sig",
        ) as file:
            data = json.load(file)

        if isinstance(data, list):
            return pd.DataFrame(data)

        if isinstance(data, dict):
            if (
                "data" in data
                and isinstance(data["data"], list)
            ):
                return pd.DataFrame(data["data"])

            return pd.DataFrame([data])

        raise CleaningError(
            "La estructura JSON no es compatible."
        )

    raise CleaningError(
        f"Formato no soportado: {extension}"
    )


def normalize_column_names(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    dataframe = dataframe.copy()

    dataframe.columns = [
        str(column)
        .strip()
        .lower()
        for column in dataframe.columns
    ]

    return dataframe


def validate_columns(
    dataframe: pd.DataFrame,
):
    actual_columns = set(dataframe.columns)
    expected_columns = set(EXPECTED_COLUMNS)

    missing = sorted(
        expected_columns - actual_columns
    )

    extra = sorted(
        actual_columns - expected_columns
    )

    if missing:
        raise CleaningError(
            "Faltan columnas obligatorias: "
            + ", ".join(missing)
        )

    return extra


def clean_string(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if not text:
        return None

    if text.endswith(".0"):
        numeric_part = text[:-2]

        if numeric_part.isdigit():
            return numeric_part

    return text


def clean_amount(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, Decimal):
        return value

    text = str(value).strip()

    if text == "-":
        return Decimal("0")

    if not text:
        return None

    normalized = text.replace(",", "")

    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(
            f"Valor monetario invalido: {value!r}"
        ) from exc


def clean_dataframe(
    dataframe: pd.DataFrame,
):
    dataframe = normalize_column_names(
        dataframe
    )

    extra_columns = validate_columns(
        dataframe
    )

    if extra_columns:
        print()
        print(
            "ADVERTENCIA: se ignoraran "
            "columnas adicionales:"
        )

        for column in extra_columns:
            print(f"  - {column}")

    cleaned = dataframe[
        list(EXPECTED_COLUMNS)
    ].copy()

    for column in STRING_COLUMNS:
        cleaned[column] = cleaned[
            column
        ].map(clean_string)

    errors = []
    dash_count = 0
    empty_amount_count = 0
    amount_count = 0

    for column in AMOUNT_COLUMNS:
        cleaned_values = []

        for index, value in cleaned[
            column
        ].items():
            raw_text = (
                ""
                if value is None
                else str(value).strip()
            )

            if raw_text == "-":
                dash_count += 1

            try:
                cleaned_value = clean_amount(
                    value
                )
            except ValueError:
                errors.append(
                    {
                        "fila": int(index) + 2,
                        "columna": column,
                        "valor": value,
                    }
                )

                cleaned_value = None

            if cleaned_value is None:
                empty_amount_count += 1
            else:
                amount_count += 1

            cleaned_values.append(
                cleaned_value
            )

        cleaned[column] = cleaned_values

    return (
        cleaned,
        errors,
        dash_count,
        empty_amount_count,
        amount_count,
    )


def save_errors(
    errors: list[dict],
    output_dir: Path,
):
    if not errors:
        return None

    output_path = (
        output_dir
        / "errores_limpieza.csv"
    )

    pd.DataFrame(errors).to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    return output_path


def decimal_to_export(value):
    if value is None:
        return ""

    if isinstance(value, Decimal):
        return format(value, "f")

    return value


def save_clean_csv(
    dataframe: pd.DataFrame,
    source_path: Path,
    output_dir: Path,
):
    output_path = (
        output_dir
        / f"{source_path.stem}_limpio.csv"
    )

    export_dataframe = dataframe.copy()

    for column in AMOUNT_COLUMNS:
        export_dataframe[column] = (
            export_dataframe[column]
            .map(decimal_to_export)
        )

    export_dataframe.to_csv(
        output_path,
        index=False,
        encoding="utf-8",
    )

    return output_path


def print_summary(
    dataframe: pd.DataFrame,
    errors: list[dict],
    dash_count: int,
    empty_amount_count: int,
    amount_count: int,
):
    print()
    print("=" * 80)
    print("RESUMEN DE LIMPIEZA")
    print("=" * 80)

    print(
        f"Filas procesadas             : "
        f"{len(dataframe):,}"
    )

    print(
        f"Columnas procesadas          : "
        f"{len(dataframe.columns)}"
    )

    print(
        f"Columnas STRING              : "
        f"{len(STRING_COLUMNS)}"
    )

    print(
        f"Columnas NUMERIC             : "
        f"{len(AMOUNT_COLUMNS)}"
    )

    print(
        f"Importes numericos validos   : "
        f"{amount_count:,}"
    )

    print(
        f"Guiones convertidos a cero   : "
        f"{dash_count:,}"
    )

    print(
        f"Importes vacios / NULL       : "
        f"{empty_amount_count:,}"
    )

    print(
        f"Errores monetarios           : "
        f"{len(errors):,}"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Limpia un archivo de presupuesto "
            "antes de cargarlo a BigQuery."
        )
    )

    parser.add_argument(
        "archivo",
        help=(
            "Ruta del archivo "
            ".csv, .xlsx, .xlsm o .json"
        ),
    )

    parser.add_argument(
        "--sheet",
        default="0",
        help=(
            "Nombre o indice de hoja Excel. "
            "Por defecto usa la primera."
        ),
    )

    args = parser.parse_args()

    source_path = Path(
        args.archivo
    ).expanduser().resolve()

    if not source_path.exists():
        print(
            f"ERROR: no existe el archivo: "
            f"{source_path}"
        )

        sys.exit(1)

    output_dir = (
        Path(__file__).resolve().parent
        / "salidas"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    sheet = args.sheet

    if (
        isinstance(sheet, str)
        and sheet.isdigit()
    ):
        sheet = int(sheet)

    print()
    print("=" * 80)
    print("LIMPIEZA DE PRESUPUESTO")
    print("=" * 80)

    print()
    print(f"Archivo : {source_path}")
    print(
        f"Formato : "
        f"{source_path.suffix.lower()}"
    )

    print()
    print("Cargando archivo...")

    try:
        dataframe = load_file(
            source_path,
            sheet_name=sheet,
        )

        print(
            f"Archivo cargado: "
            f"{len(dataframe):,} filas"
        )

        (
            cleaned,
            errors,
            dash_count,
            empty_amount_count,
            amount_count,
        ) = clean_dataframe(
            dataframe
        )

    except Exception as exc:
        print()
        print("ERROR DURANTE LA LIMPIEZA")
        print(type(exc).__name__)
        print(str(exc))

        sys.exit(1)

    print_summary(
        cleaned,
        errors,
        dash_count,
        empty_amount_count,
        amount_count,
    )

    if errors:
        errors_path = save_errors(
            errors,
            output_dir,
        )

        print()
        print(
            "RESULTADO: NO APTO PARA "
            "CARGAR A BIGQUERY"
        )

        print()
        print(
            f"Revisar errores en:"
        )
        print(errors_path)

        sys.exit(2)

    clean_path = save_clean_csv(
        cleaned,
        source_path,
        output_dir,
    )

    print()
    print(
        "RESULTADO: ARCHIVO LIMPIO"
    )

    print()
    print(
        "Archivo generado:"
    )
    print(clean_path)


if __name__ == "__main__":
    main()