import json

import pandas as pd
import pytest

from database.bootstrap.source_loader import (
    SourceLoadError,
    load_source,
)


pytestmark = pytest.mark.unit


def test_load_csv(tmp_path):
    path = tmp_path / "source.csv"

    path.write_text(
        "pais,valor\nPERU,100\n",
        encoding="utf-8",
    )

    dataframe = load_source(path)

    assert len(dataframe) == 1
    assert dataframe.loc[0, "pais"] == "PERU"


def test_load_json_list(tmp_path):
    path = tmp_path / "source.json"

    path.write_text(
        json.dumps(
            [
                {
                    "pais": "PERU",
                    "valor": 100,
                }
            ]
        ),
        encoding="utf-8",
    )

    dataframe = load_source(path)

    assert len(dataframe) == 1


def test_load_excel(tmp_path):
    path = tmp_path / "source.xlsx"

    source = pd.DataFrame(
        [
            {
                "pais": "PERU",
                "valor": 100,
            }
        ]
    )

    source.to_excel(
        path,
        index=False,
    )

    dataframe = load_source(path)

    assert len(dataframe) == 1

    assert (
        dataframe.loc[
            0,
            "pais",
        ]
        == "PERU"
    )


def test_missing_file_is_rejected(
    tmp_path,
):
    path = (
        tmp_path
        / "missing.xlsx"
    )

    with pytest.raises(
        SourceLoadError,
        match="No existe",
    ):
        load_source(path)


def test_unsupported_extension_is_rejected(
    tmp_path,
):
    path = (
        tmp_path
        / "source.txt"
    )

    path.write_text(
        "test",
        encoding="utf-8",
    )

    with pytest.raises(
        SourceLoadError,
        match="Formato no soportado",
    ):
        load_source(path)