import pandas as pd
import pytest

from app.config.presupuesto_schema import (
    LEGACY_EXPECTED_COLUMNS,
)
from database.cli import (
    main,
    parse_sheet,
)


pytestmark = pytest.mark.unit


def make_source_file(
    tmp_path,
):
    row = {
        column: ""
        for column
        in LEGACY_EXPECTED_COLUMNS
    }

    row.update(
        {
            "pais": "PERU",
            "vp": "VP",
            "vp2": "VP2",
            "nombre_gasto": "PRUEBA",
            "enero_usd": "100",
            "anio_usd": "100",
        }
    )

    path = (
        tmp_path
        / "presupuesto.csv"
    )

    pd.DataFrame(
        [row]
    ).to_csv(
        path,
        index=False,
        encoding="utf-8",
    )

    return path


def test_parse_sheet_number():
    assert parse_sheet(
        "0"
    ) == 0


def test_parse_sheet_name():
    assert parse_sheet(
        "Presupuesto"
    ) == "Presupuesto"


def test_prepare_command_success(
    tmp_path,
    capsys,
):
    path = make_source_file(
        tmp_path
    )

    exit_code = main(
        [
            "prepare",
            "--file",
            str(path),
            "--actor",
            "test@ransa.net",
        ]
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert exit_code == 0

    assert (
        "RESULTADO               : OK"
        in output
    )

    assert (
        "Columnas finales        : 67"
        in output
    )

    assert (
        "No se realizo ningun "
        "cambio en BigQuery."
        in output
    )


def test_prepare_command_missing_file(
    tmp_path,
    capsys,
):
    path = (
        tmp_path
        / "no_existe.xlsx"
    )

    exit_code = main(
        [
            "prepare",
            "--file",
            str(path),
            "--actor",
            "test@ransa.net",
        ]
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert exit_code == 2

    assert (
        "ERROR DE PREPARACION"
        in output
    )