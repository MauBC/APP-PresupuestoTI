import json
from pathlib import Path

import pandas as pd


class SourceLoadError(ValueError):
    pass


SUPPORTED_EXTENSIONS = (
    ".csv",
    ".xlsx",
    ".xlsm",
    ".json",
)


def load_csv(
    file_path: Path,
) -> pd.DataFrame:
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

    raise SourceLoadError(
        "No se pudo detectar la codificacion del CSV."
    ) from last_error


def load_json(
    file_path: Path,
) -> pd.DataFrame:
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
            and isinstance(
                data["data"],
                list,
            )
        ):
            return pd.DataFrame(
                data["data"]
            )

        return pd.DataFrame(
            [data]
        )

    raise SourceLoadError(
        "La estructura JSON no es compatible."
    )


def load_source(
    file_path: str | Path,
    *,
    sheet_name=0,
) -> pd.DataFrame:
    path = (
        Path(file_path)
        .expanduser()
        .resolve()
    )

    if not path.exists():
        raise SourceLoadError(
            f"No existe el archivo: {path}"
        )

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise SourceLoadError(
            "Formato no soportado: "
            f"{extension}"
        )

    if extension == ".csv":
        return load_csv(path)

    if extension in {
        ".xlsx",
        ".xlsm",
    }:
        return pd.read_excel(
            path,
            sheet_name=sheet_name,
            dtype=object,
            keep_default_na=False,
        )

    return load_json(path)