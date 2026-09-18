import pytest

from app.models.opex_master_data import (
    OpexAccountMasterRecord,
    OpexCebeMasterRecord,
    OpexMasterConflict,
    OpexMasterDataSnapshot,
    OpexMasterSource,
    OpexRecoverableMasterRecord,
)
from app.services.opex_master_enrichment_service import (
    OpexMasterEnrichmentError,
    OpexMasterEnrichmentService,
)


pytestmark = pytest.mark.unit


SOURCE = OpexMasterSource(
    path="test.xlsx",
    sheet_name="Sheet1",
    header_row=1,
    physical_rows=1,
    unique_rows=1,
    duplicate_rows=0,
)


def make_snapshot(
    *,
    accounts=None,
    cebes=None,
    recoverables=None,
    account_conflicts=None,
    cebe_conflicts=None,
    recoverable_conflicts=None,
):
    return OpexMasterDataSnapshot(
        accounts=accounts or {},
        cebes=cebes or {},
        recoverables=(
            recoverables or {}
        ),
        account_conflicts=(
            account_conflicts or {}
        ),
        cebe_conflicts=(
            cebe_conflicts or {}
        ),
        recoverable_conflicts=(
            recoverable_conflicts or {}
        ),
        account_source=SOURCE,
        cebe_source=SOURCE,
        recoverable_source=SOURCE,
    )


def valid_account(
    key="600000001",
):
    return OpexAccountMasterRecord(
        numero_cuenta=key,
        categoria_gasto="SERVICIOS",
        nombre_cuenta="CUENTA TEST",
        atributo_2="ATRIBUTO TEST",
    )


def valid_cebe(
    key="04WF2EAF90",
):
    return OpexCebeMasterRecord(
        centro_beneficio=key,
        desc_cebe="CEBE TEST",
        macroservicio_cg="MACRO",
        tipo_servicio_cg="TIPO",
        region_cg="REGION",
        sede_cg="SEDE",
        segmentacion="SEGMENTO",
    )


def recoverable(
    key,
    *,
    sociedad=None,
    compania=None,
    pais=None,
):
    return OpexRecoverableMasterRecord(
        inicial=key,
        sociedad=(
            sociedad or key
        ),
        compania=(
            compania
            or f"EMPRESA {key}"
        ),
        pais=(
            pais or "PE"
        ),
    )


@pytest.mark.parametrize(
    ("final_digit", "expected"),
    (
        (
            "1",
            "COSTOS VARIABLES",
        ),
        (
            "2",
            "COSTOS FIJOS DIRECTOS",
        ),
        (
            "3",
            "COSTOS FIJOS INDIRECTOS",
        ),
        (
            "4",
            "GASTOS DE ADMINISTRACIÓN",
        ),
        (
            "5",
            "GASTOS DE VENTAS",
        ),
        (
            "7",
            "OTROS I/E OPERATIVOS",
        ),
    ),
)
def test_gyp_mapping(
    final_digit,
    expected,
):
    service = (
        OpexMasterEnrichmentService(
            make_snapshot()
        )
    )

    assert (
        service.derive_gyp_from_ceco(
            f"04WF2EAF9{final_digit}"
        )
        == expected
    )


@pytest.mark.parametrize(
    "final_value",
    (
        "0",
        "6",
        "8",
        "9",
        "A",
    ),
)
def test_unknown_gyp_value_returns_none(
    final_value,
):
    service = (
        OpexMasterEnrichmentService(
            make_snapshot()
        )
    )

    assert (
        service.derive_gyp_from_ceco(
            f"04WF2EAF9{final_value}"
        )
        is None
    )


def test_derive_cebe_preserves_leading_zero():
    service = (
        OpexMasterEnrichmentService(
            make_snapshot()
        )
    )

    assert (
        service.derive_cebe_from_ceco(
            "04WF2EAF93"
        )
        == "04WF2EAF90"
    )


@pytest.mark.parametrize(
    ("prefix", "ceco"),
    (
        (
            "1",
            "01ABCDEF01",
        ),
        (
            "4",
            "04WF2EAF93",
        ),
        (
            "5",
            "05ABCDEFG1",
        ),
    ),
)
def test_single_digit_recoverable_matches_zero_padded_ceco(
    prefix,
    ceco,
):
    snapshot = make_snapshot(
        recoverables={
            prefix: recoverable(
                prefix
            ),
        }
    )

    service = (
        OpexMasterEnrichmentService(
            snapshot
        )
    )

    resolved_prefix, _ = (
        service.resolve_recoverable(
            ceco
        )
    )

    assert (
        resolved_prefix
        == prefix
    )


@pytest.mark.parametrize(
    ("prefix", "ceco"),
    (("1", "10ABCDEF01"), ("4", "41WF2EAF93"), ("5", "51DL1NA092")),
)
def test_single_digit_recoverable_does_not_capture_unpadded_ceco(prefix, ceco):
    service = OpexMasterEnrichmentService(
        make_snapshot(recoverables={prefix: recoverable(prefix, pais="CO")})
    )

    with pytest.raises(OpexMasterEnrichmentError) as error:
        service.resolve_recoverable(ceco)

    assert error.value.code == "RECOVERABLE_NOT_FOUND"
    assert error.value.key == ceco
    assert ceco in str(error.value)


@pytest.mark.parametrize("ceco", ("51AD000SA7", "51AD000CC7"))
def test_full_alphanumeric_recoverable_wins_over_shorter_prefixes(ceco):
    service = OpexMasterEnrichmentService(
        make_snapshot(recoverables={
            "5": recoverable("5", pais="CO"),
            "51": recoverable("51", compania="GENERAL", pais="PE"),
            "51AD": recoverable("51AD", compania="INTERMEDIA", pais="PE"),
            ceco: recoverable(ceco, compania="ESPECIFICA", pais="PE"),
        })
    )

    prefix, record = service.resolve_recoverable(ceco)

    assert prefix == ceco
    assert record.compania == "ESPECIFICA"
    assert record.pais == "PE"


def test_zero_padded_recoverable_alias_collision_requires_resolution():
    service = OpexMasterEnrichmentService(
        make_snapshot(recoverables={
            "5": recoverable("5", compania="PRIMERA"),
            "05": recoverable("05", compania="SEGUNDA"),
        })
    )

    with pytest.raises(OpexMasterEnrichmentError) as error:
        service.resolve_recoverable("05ABCDEFG1")

    assert error.value.code == "RECOVERABLE_PREFIX_AMBIGUOUS"


def test_longest_recoverable_prefix_wins():
    snapshot = make_snapshot(
        recoverables={
            "1": recoverable(
                "1"
            ),
            "1000": recoverable(
                "1000"
            ),
        }
    )

    service = (
        OpexMasterEnrichmentService(
            snapshot
        )
    )

    prefix, _ = (
        service.resolve_recoverable(
            "1000ABCDEF1"
        )
    )

    assert prefix == "1000"


def test_missing_account_is_blocker():
    service = (
        OpexMasterEnrichmentService(
            make_snapshot()
        )
    )

    with pytest.raises(
        OpexMasterEnrichmentError,
    ) as error:
        service.resolve_account(
            "999999999"
        )

    assert (
        error.value.code
        == "ACCOUNT_NOT_FOUND"
    )


def test_ambiguous_account_is_blocker_and_exposes_options():
    first = (
        OpexAccountMasterRecord(
            numero_cuenta="625110004",
            categoria_gasto="Beneficios",
            nombre_cuenta=(
                "ACTIVIDADES Y EVENTOS"
            ),
            atributo_2=(
                "I/E REEMBOLSABLES"
            ),
        )
    )

    second = (
        OpexAccountMasterRecord(
            numero_cuenta="625110004",
            categoria_gasto="Beneficios",
            nombre_cuenta=(
                "ACTIVIDADES Y EVENTOS"
            ),
            atributo_2="X",
        )
    )

    snapshot = make_snapshot(
        account_conflicts={
            "625110004": (
                OpexMasterConflict(
                    key="625110004",
                    locations=(
                        "Sheet1:2",
                        "Sheet1:4",
                    ),
                    records=(
                        first,
                        second,
                    ),
                )
            )
        }
    )

    service = (
        OpexMasterEnrichmentService(
            snapshot
        )
    )

    assert len(
        service.account_options(
            "625110004"
        )
    ) == 2

    with pytest.raises(
        OpexMasterEnrichmentError,
    ) as error:
        service.resolve_account(
            "625110004"
        )

    assert (
        error.value.code
        == "ACCOUNT_AMBIGUOUS"
    )


def test_missing_required_account_data_is_blocker():
    record = (
        OpexAccountMasterRecord(
            numero_cuenta="600",
            categoria_gasto="CAT",
            nombre_cuenta=None,
            atributo_2="ATR",
        )
    )

    service = (
        OpexMasterEnrichmentService(
            make_snapshot(
                accounts={
                    "600": record,
                }
            )
        )
    )

    with pytest.raises(
        OpexMasterEnrichmentError,
    ) as error:
        service.resolve_account(
            "600"
        )

    assert (
        error.value.code
        == "ACCOUNT_DATA_MISSING"
    )


def test_missing_cebe_is_blocker():
    service = (
        OpexMasterEnrichmentService(
            make_snapshot()
        )
    )

    with pytest.raises(
        OpexMasterEnrichmentError,
    ) as error:
        service.resolve_cebe(
            "04WF2EAF90"
        )

    assert (
        error.value.code
        == "CEBE_NOT_FOUND"
    )


def test_ambiguous_cebe_is_blocker():
    first = valid_cebe(
        "04WF2EAF90"
    )

    second = (
        OpexCebeMasterRecord(
            centro_beneficio=(
                "04WF2EAF90"
            ),
            desc_cebe="OTRO",
            macroservicio_cg="MACRO",
            tipo_servicio_cg="TIPO",
            region_cg="REGION",
            sede_cg="SEDE",
            segmentacion="SEG",
        )
    )

    snapshot = make_snapshot(
        cebe_conflicts={
            "04WF2EAF90": (
                OpexMasterConflict(
                    key="04WF2EAF90",
                    locations=(
                        "Sheet1:1",
                        "Sheet1:2",
                    ),
                    records=(
                        first,
                        second,
                    ),
                )
            )
        }
    )

    service = (
        OpexMasterEnrichmentService(
            snapshot
        )
    )

    with pytest.raises(
        OpexMasterEnrichmentError,
    ) as error:
        service.resolve_cebe(
            "04WF2EAF90"
        )

    assert (
        error.value.code
        == "CEBE_AMBIGUOUS"
    )


def test_full_enrichment():
    account = valid_account()

    cebe = valid_cebe()

    rec = (
        OpexRecoverableMasterRecord(
            inicial="4",
            sociedad="2504",
            compania=(
                "Colombia Almacenes"
            ),
            pais="CO",
        )
    )

    snapshot = make_snapshot(
        accounts={
            account.numero_cuenta: (
                account
            ),
        },
        cebes={
            cebe.centro_beneficio: (
                cebe
            ),
        },
        recoverables={
            "4": rec,
        },
    )

    service = (
        OpexMasterEnrichmentService(
            snapshot
        )
    )

    result = service.enrich(
        numero_cuenta="600000001",
        ceco="04WF2EAF93",
    )

    assert (
        result.numero_cuenta
        == "600000001"
    )

    assert (
        result.ceco
        == "04WF2EAF93"
    )

    assert (
        result.centro_beneficio
        == "04WF2EAF90"
    )

    assert (
        result.ceco_prefix
        == "4"
    )

    assert (
        result.compania
        == "Colombia Almacenes"
    )

    assert result.pais == "CO"

    assert (
        result.gyp
        == "COSTOS FIJOS INDIRECTOS"
    )

    assert (
        result.segmentacion
        == "SEGMENTO"
    )



def test_derive_cebe_does_not_require_gyp_mapping():
    service = (
        OpexMasterEnrichmentService(
            make_snapshot()
        )
    )

    assert (
        service.derive_cebe_from_ceco(
            "51AD000CC6"
        )
        == "51AD000CC0"
    )


def test_missing_cebe_keeps_ceco_and_leaves_cebe_fields_blank():
    rec = recoverable(
        "51AD000CC6",
        sociedad="2501",
        compania="SLA",
        pais="PE",
    )

    service = (
        OpexMasterEnrichmentService(
            make_snapshot(
                recoverables={
                    "51AD000CC6":
                        rec,
                }
            )
        )
    )

    result = service.enrich_ceco(
        "51AD000CC6"
    )

    assert (
        result.ceco
        == "51AD000CC6"
    )

    assert (
        result.ceco_prefix
        == "51AD000CC6"
    )

    assert result.gyp is None

    assert (
        result.centro_beneficio
        is None
    )

    assert result.desc_cebe is None

    assert (
        result.macroservicio_cg
        is None
    )

    assert (
        result.tipo_servicio_cg
        is None
    )

    assert result.region_cg is None
    assert result.sede_cg is None
    assert result.segmentacion is None
