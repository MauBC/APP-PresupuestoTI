import pandas as pd
import pytest

from app.services.opex_master_data_loader import (
    OpexMasterDataError,
    OpexMasterDataLoader,
)


pytestmark = pytest.mark.unit


def write_excel(
    path,
    rows,
    *,
    sheet="Datos",
):
    pd.DataFrame(
        rows
    ).to_excel(
        path,
        sheet_name=sheet,
        index=False,
        header=False,
    )


def create_valid_masters(
    directory,
):
    write_excel(
        directory / "CUENTA.xlsx",
        (
            ("titulo", "", "", ""),
            (
                "CUENTA",
                "CATEGORIA GASTO",
                "Nombre Cuenta",
                "Atributo 2",
            ),
            (
                635610007,
                "SERVICIOS",
                "CUENTA TEST",
                "ATRIBUTO TEST",
            ),
        ),
    )

    write_excel(
        directory / "CEBE.xlsx",
        (
            (
                "Centro de beneficio",
                "Desc_CeBe",
                "Macroservicio CG",
                "Tipo Servicio CG",
                "Región CG",
                "Sede CG",
                "Seg Rs",
            ),
            (
                "291ACC9900",
                "CEBE TEST",
                "MACRO",
                "TIPO",
                "LIMA",
                "SEDE",
                "SEGMENTO",
            ),
        ),
    )

    write_excel(
        directory / "RECUPERABLES.xlsx",
        (
            (
                "Inicial",
                "Sociedad",
                "Descripción Sociedad",
                "País",
            ),
            (
                291,
                291,
                "Alma Peru",
                "PE",
            ),
            (
                "04",
                "2504",
                "Colombia Almacenes",
                "CO",
            ),
        ),
    )


def test_loads_three_master_indexes(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    snapshot = (
        OpexMasterDataLoader(
            tmp_path
        )
        .load()
    )

    assert (
        "635610007"
        in snapshot.accounts
    )

    assert (
        "291ACC9900"
        in snapshot.cebes
    )

    assert (
        "291"
        in snapshot.recoverables
    )


def test_detects_header_below_first_row(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    snapshot = (
        OpexMasterDataLoader(
            tmp_path
        )
        .load()
    )

    assert (
        snapshot
        .account_source
        .header_row
        == 2
    )


def test_preserves_leading_zero_codes(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    snapshot = (
        OpexMasterDataLoader(
            tmp_path
        )
        .load()
    )

    assert (
        "04"
        in snapshot.recoverables
    )


def test_account_numeric_code_becomes_clean_string(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    snapshot = (
        OpexMasterDataLoader(
            tmp_path
        )
        .load()
    )

    assert (
        snapshot.accounts[
            "635610007"
        ].numero_cuenta
        == "635610007"
    )


def test_identical_duplicate_is_deduplicated(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    write_excel(
        tmp_path / "CUENTA.xlsx",
        (
            (
                "CUENTA",
                "CATEGORIA GASTO",
                "Nombre Cuenta",
                "Atributo 2",
            ),
            (
                100,
                "CAT",
                "CUENTA",
                "A",
            ),
            (
                100,
                "CAT",
                "CUENTA",
                "A",
            ),
        ),
    )

    snapshot = (
        OpexMasterDataLoader(
            tmp_path
        )
        .load()
    )

    assert len(
        snapshot.accounts
    ) == 1

    assert (
        snapshot
        .account_source
        .duplicate_rows
        == 1
    )


def test_conflicting_account_duplicate_is_isolated(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    write_excel(
        tmp_path / "CUENTA.xlsx",
        (
            (
                "CUENTA",
                "CATEGORIA GASTO",
                "Nombre Cuenta",
                "Atributo 2",
            ),
            (
                100,
                "CAT A",
                "CUENTA",
                "A",
            ),
            (
                100,
                "CAT B",
                "CUENTA",
                "A",
            ),
        ),
    )

    snapshot = (
        OpexMasterDataLoader(
            tmp_path
        )
        .load()
    )

    assert (
        "100"
        not in snapshot.accounts
    )

    assert (
        "100"
        in snapshot.account_conflicts
    )

    conflict = (
        snapshot.account_conflicts[
            "100"
        ]
    )

    assert len(
        conflict.locations
    ) == 2

    assert len(
        conflict.records
    ) == 2


def test_conflicting_cebe_duplicate_is_isolated(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    write_excel(
        tmp_path / "CEBE.xlsx",
        (
            (
                "Centro de beneficio",
                "Desc_CeBe",
                "Macroservicio CG",
                "Tipo Servicio CG",
                "Región CG",
                "Sede CG",
                "Seg Rs",
            ),
            (
                "AAA0",
                "UNO",
                "M",
                "T",
                "R",
                "S",
                "SEG",
            ),
            (
                "AAA0",
                "DOS",
                "M",
                "T",
                "R",
                "S",
                "SEG",
            ),
        ),
    )

    snapshot = (
        OpexMasterDataLoader(
            tmp_path
        )
        .load()
    )

    assert (
        "AAA0"
        not in snapshot.cebes
    )

    assert (
        "AAA0"
        in snapshot.cebe_conflicts
    )

    conflict = (
        snapshot.cebe_conflicts[
            "AAA0"
        ]
    )

    assert len(
        conflict.locations
    ) == 2


def test_conflicting_recoverable_duplicate_is_isolated(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    write_excel(
        tmp_path / "RECUPERABLES.xlsx",
        (
            (
                "Inicial",
                "Sociedad",
                "Descripción Sociedad",
                "País",
            ),
            (
                "291",
                "291",
                "EMPRESA A",
                "PE",
            ),
            (
                "291",
                "291",
                "EMPRESA B",
                "PE",
            ),
        ),
    )

    snapshot = (
        OpexMasterDataLoader(
            tmp_path
        )
        .load()
    )

    assert (
        "291"
        not in snapshot.recoverables
    )

    assert (
        "291"
        in snapshot.recoverable_conflicts
    )

    conflict = (
        snapshot.recoverable_conflicts[
            "291"
        ]
    )

    assert len(
        conflict.locations
    ) == 2


def test_missing_expected_headers_is_rejected(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    write_excel(
        tmp_path / "CUENTA.xlsx",
        (
            (
                "OTRA COLUMNA",
                "OTRA",
            ),
            (
                1,
                2,
            ),
        ),
    )

    with pytest.raises(
        OpexMasterDataError,
        match="encabezados esperados",
    ):
        (
            OpexMasterDataLoader(
                tmp_path
            )
            .load()
        )


def test_account_master_with_only_blank_keys_is_rejected(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    write_excel(
        tmp_path / "CUENTA.xlsx",
        (
            (
                "CUENTA",
                "CATEGORIA GASTO",
                "Nombre Cuenta",
                "Atributo 2",
            ),
            (
                "",
                "CAT",
                "NOMBRE",
                "A",
            ),
        ),
    )

    with pytest.raises(
        OpexMasterDataError,
        match="no contiene cuentas utilizables",
    ):
        (
            OpexMasterDataLoader(
                tmp_path
            )
            .load()
        )

def test_account_dirty_rows_are_ignored(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    write_excel(
        tmp_path / "CUENTA.xlsx",
        (
            (
                "CUENTA",
                "CATEGORIA GASTO",
                "Nombre Cuenta",
                "Atributo 2",
            ),
            (
                635610007,
                "SERVICIOS",
                "CUENTA VALIDA",
                "ATRIBUTO",
            ),
            (
                "XL",
                "Salarios y Sueldos",
                "Incremento AFP",
                "SUELDOS Y SALARIOS",
            ),
            (
                "PROYECTO",
                "Salarios y Sueldos",
                "Proyecto",
                "SEGUROS",
            ),
            (
                "",
                "",
                "INCREMENTO SALARIAL",
                "SEGUROS",
            ),
            (
                "",
                "",
                "",
                "SUELDOS Y SALARIOS",
            ),
        ),
    )

    snapshot = (
        OpexMasterDataLoader(
            tmp_path
        )
        .load()
    )

    assert set(
        snapshot.accounts
    ) == {
        "635610007",
    }

    assert (
        snapshot
        .account_source
        .ignored_invalid_key_rows
        == 2
    )

    assert (
        snapshot
        .account_source
        .ignored_blank_key_rows
        == 2
    )


def test_recoverable_dirty_keys_are_ignored(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    write_excel(
        tmp_path / "RECUPERABLES.xlsx",
        (
            (
                "Inicial",
                "Sociedad",
                "Descripción Sociedad",
                "País",
            ),
            (
                "04",
                "2504",
                "Colombia Almacenes",
                "CO",
            ),
            (
                "291",
                "291",
                "Alma Peru",
                "PE",
            ),
            (
                "TOTAL",
                "",
                "",
                "",
            ),
            (
                "",
                "",
                "Texto residual",
                "",
            ),
        ),
    )

    snapshot = (
        OpexMasterDataLoader(
            tmp_path
        )
        .load()
    )

    assert set(
        snapshot.recoverables
    ) == {
        "04",
        "291",
    }

    assert (
        snapshot
        .recoverable_source
        .ignored_invalid_key_rows
        == 1
    )

    assert (
        snapshot
        .recoverable_source
        .ignored_blank_key_rows
        == 1
    )



def test_cebe_dirty_keys_are_ignored(
    tmp_path,
):
    create_valid_masters(
        tmp_path
    )

    write_excel(
        tmp_path / "CEBE.xlsx",
        (
            (
                "Centro de beneficio",
                "Desc_CeBe",
                "Macroservicio CG",
                "Tipo Servicio CG",
                "Región CG",
                "Sede CG",
                "Seg Rs",
            ),
            (
                "291ACC9900",
                "CEBE PERU",
                "MACRO",
                "TIPO",
                "LIMA",
                "SEDE",
                "SEG",
            ),
            (
                "04WF2EAF90",
                "CEBE COLOMBIA",
                "MACRO",
                "TIPO",
                "BOGOTA",
                "SEDE",
                "SEG",
            ),
            (
                "X",
                "RUIDO",
                "M",
                "T",
                "R",
                "S",
                "SEG",
            ),
            (
                "R&A",
                "RUIDO",
                "M",
                "T",
                "R",
                "S",
                "SEG",
            ),
            (
                "NICARAGUA",
                "RUIDO",
                "M",
                "T",
                "R",
                "S",
                "SEG",
            ),
            (
                "COSTA RICA",
                "RUIDO",
                "M",
                "T",
                "R",
                "S",
                "SEG",
            ),
        ),
    )

    snapshot = (
        OpexMasterDataLoader(
            tmp_path
        )
        .load()
    )

    assert set(
        snapshot.cebes
    ) == {
        "291ACC9900",
        "04WF2EAF90",
    }

    assert (
        snapshot
        .cebe_source
        .ignored_invalid_key_rows
        == 4
    )

    assert not (
        {
            "X",
            "R&A",
            "NICARAGUA",
            "COSTA RICA",
        }
        & set(
            snapshot.cebes
        )
    )
