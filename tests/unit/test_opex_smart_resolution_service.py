from decimal import Decimal

import pytest

from app.models.opex_master_data import (
    OpexAccountMasterRecord,
    OpexCebeMasterRecord,
    OpexMasterConflict,
    OpexMasterDataSnapshot,
    OpexMasterSource,
    OpexRecoverableMasterRecord,
)
from app.models.opex_smart_template import (
    OpexTemplateBudget,
    OpexTemplateDistribution,
)
from app.services.opex_master_enrichment_service import (
    OpexMasterEnrichmentService,
)
from app.services.opex_smart_resolution_service import (
    OpexSmartResolutionError,
    OpexSmartResolutionService,
)
from app.services.opex_template_distribution_service import (
    OpexTemplateResolvedDistribution,
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


ACCOUNT_ADM_A = OpexAccountMasterRecord(
    numero_cuenta="600000001",
    categoria_gasto="Equipo informático",
    nombre_cuenta="SOFTWARE ADM",
    atributo_2="A",
)

ACCOUNT_ADM_B = OpexAccountMasterRecord(
    numero_cuenta="600000001",
    categoria_gasto="Equipo informático",
    nombre_cuenta="SOFTWARE ADM",
    atributo_2="B",
)

ACCOUNT_VTAS_A = OpexAccountMasterRecord(
    numero_cuenta="600000001",
    categoria_gasto="Equipo informático",
    nombre_cuenta="SOFTWARE VTAS",
    atributo_2="A",
)

ACCOUNT_VTAS_C = OpexAccountMasterRecord(
    numero_cuenta="600000001",
    categoria_gasto="Equipo informático",
    nombre_cuenta="SOFTWARE VTAS",
    atributo_2="C",
)


CEBE_A = OpexCebeMasterRecord(
    centro_beneficio="04WF2EAF90",
    desc_cebe="CEBE A",
    macroservicio_cg="MACRO A",
    tipo_servicio_cg="TIPO A",
    region_cg="REGION A",
    sede_cg="SEDE A",
    segmentacion="SEG A",
)

CEBE_B = OpexCebeMasterRecord(
    centro_beneficio="04WF2EAF90",
    desc_cebe="CEBE B",
    macroservicio_cg="MACRO B",
    tipo_servicio_cg="TIPO B",
    region_cg="REGION B",
    sede_cg="SEDE B",
    segmentacion="SEG B",
)

CEBE_291 = OpexCebeMasterRecord(
    centro_beneficio="291ACC9900",
    desc_cebe="CEBE 291",
    macroservicio_cg="MACRO 291",
    tipo_servicio_cg="TIPO 291",
    region_cg="REGION 291",
    sede_cg="SEDE 291",
    segmentacion="SEG 291",
)


def snapshot():
    return OpexMasterDataSnapshot(
        accounts={},
        cebes={
            "291ACC9900": (
                CEBE_291
            ),
        },
        recoverables={
            "4": (
                OpexRecoverableMasterRecord(
                    inicial="4",
                    sociedad="2504",
                    compania=(
                        "Colombia Almacenes"
                    ),
                    pais="CO",
                )
            ),
            "291": (
                OpexRecoverableMasterRecord(
                    inicial="291",
                    sociedad="291",
                    compania="Alma Peru",
                    pais="PE",
                )
            ),
        },
        account_conflicts={
            "600000001": (
                OpexMasterConflict(
                    key="600000001",
                    locations=(
                        "A",
                        "B",
                        "C",
                        "D",
                    ),
                    records=(
                        ACCOUNT_ADM_A,
                        ACCOUNT_ADM_B,
                        ACCOUNT_VTAS_A,
                        ACCOUNT_VTAS_C,
                    ),
                )
            )
        },
        cebe_conflicts={
            "04WF2EAF90": (
                OpexMasterConflict(
                    key="04WF2EAF90",
                    locations=(
                        "A",
                        "B",
                    ),
                    records=(
                        CEBE_A,
                        CEBE_B,
                    ),
                )
            )
        },
        recoverable_conflicts={},
        account_source=SOURCE,
        cebe_source=SOURCE,
        recoverable_source=SOURCE,
    )


def service():
    return OpexSmartResolutionService(
        OpexMasterEnrichmentService(
            snapshot()
        )
    )


def budget():
    return OpexTemplateBudget(
        sheet_name="Gasto 1",
        nombre_gasto="SERVICIO TEST",
        proveedor="PROVEEDOR",
        moneda_facturacion="USD",
        numero_cuenta="600000001",
        tipo="ANUAL",
        monto=Decimal("1000"),
        distributions=(
            OpexTemplateDistribution(
                excel_row=8,
                ceco="04WF2EAF93",
                percentage=(
                    Decimal("0.40")
                ),
                amount=(
                    Decimal("400")
                ),
            ),
            OpexTemplateDistribution(
                excel_row=9,
                ceco="291ACC9904",
                percentage=(
                    Decimal("0.60")
                ),
                amount=(
                    Decimal("600")
                ),
            ),
        ),
    )


def resolved():
    return OpexTemplateResolvedDistribution(
        mode="IMPORTE",
        amounts=(
            (
                "04WF2EAF93",
                Decimal("400.00"),
            ),
            (
                "291ACC9904",
                Decimal("600.00"),
            ),
        ),
    )


def test_account_options_are_grouped_for_ui():
    groups = (
        service()
        .account_choice_groups(
            "600000001"
        )
    )

    assert len(groups) == 2

    assert (
        groups[0].categoria_gasto
        == "Equipo informático"
    )

    assert (
        groups[0].nombre_cuenta
        == "SOFTWARE ADM"
    )

    assert (
        groups[0].atributos_2
        == ("A", "B")
    )

    assert (
        groups[1].nombre_cuenta
        == "SOFTWARE VTAS"
    )

    assert (
        groups[1].atributos_2
        == ("A", "C")
    )


def test_select_account_returns_exact_official_record():
    selected = (
        service()
        .select_account(
            "600000001",
            categoria_gasto=(
                "Equipo informático"
            ),
            nombre_cuenta=(
                "SOFTWARE ADM"
            ),
            atributo_2="B",
        )
    )

    assert selected == ACCOUNT_ADM_B


def test_select_account_rejects_non_official_combination():
    with pytest.raises(
        OpexSmartResolutionError,
    ) as exc_info:
        (
            service()
            .select_account(
                "600000001",
                categoria_gasto=(
                    "Equipo informático"
                ),
                nombre_cuenta=(
                    "SOFTWARE ADM"
                ),
                atributo_2="NO EXISTE",
            )
        )

    assert (
        exc_info.value.code
        == "ACCOUNT_SELECTION_INVALID"
    )


def test_cebe_requirements_group_by_derived_cebe():
    requirements = (
        service()
        .cebe_requirements(
            budget()
        )
    )

    assert len(
        requirements
    ) == 1

    requirement = (
        requirements[0]
    )

    assert (
        requirement.centro_beneficio
        == "04WF2EAF90"
    )

    assert (
        requirement.cecos
        == ("04WF2EAF93",)
    )

    assert (
        requirement.excel_rows
        == (8,)
    )

    assert (
        requirement.options
        == (
            CEBE_A,
            CEBE_B,
        )
    )


def test_build_rows_requires_explicit_ambiguous_cebe():
    with pytest.raises(
        OpexSmartResolutionError,
    ) as exc_info:
        service().build_rows(
            budget=budget(),
            resolved=resolved(),
            account_selection=(
                ACCOUNT_ADM_B
            ),
        )

    assert (
        exc_info.value.code
        == "CEBE_SELECTION_REQUIRED"
    )

    assert (
        exc_info.value.key
        == "04WF2EAF90"
    )


def test_build_rows_rejects_foreign_cebe_selection():
    foreign = (
        OpexCebeMasterRecord(
            centro_beneficio=(
                "04WF2EAF90"
            ),
            desc_cebe="INVENTADO",
            macroservicio_cg="X",
            tipo_servicio_cg="X",
            region_cg="X",
            sede_cg="X",
            segmentacion="X",
        )
    )

    with pytest.raises(
        OpexSmartResolutionError,
    ) as exc_info:
        service().build_rows(
            budget=budget(),
            resolved=resolved(),
            account_selection=(
                ACCOUNT_ADM_B
            ),
            cebe_selections={
                "04WF2EAF90": foreign,
            },
        )

    assert (
        exc_info.value.code
        == "CEBE_SELECTION_INVALID"
    )


def test_build_rows_uses_explicit_account_and_cebe():
    rows = (
        service()
        .build_rows(
            budget=budget(),
            resolved=resolved(),
            account_selection=(
                ACCOUNT_ADM_B
            ),
            cebe_selections={
                "04WF2EAF90":
                    CEBE_B,
            },
        )
    )

    assert len(rows) == 2

    first = rows[0]
    second = rows[1]

    assert (
        first.enrichment.nombre_cuenta
        == "SOFTWARE ADM"
    )

    assert (
        first.enrichment.atributo_2
        == "B"
    )

    assert (
        first.enrichment.desc_cebe
        == "CEBE B"
    )

    assert (
        first.enrichment.compania
        == "Colombia Almacenes"
    )

    assert (
        second.enrichment.desc_cebe
        == "CEBE 291"
    )

    assert (
        sum(
            row.monto_ceco
            for row in rows
        )
        == Decimal("1000.00")
    )


def test_build_rows_preserves_distribution_order():
    reversed_distribution = (
        OpexTemplateResolvedDistribution(
            mode="IMPORTE",
            amounts=(
                (
                    "291ACC9904",
                    Decimal("600"),
                ),
                (
                    "04WF2EAF93",
                    Decimal("400"),
                ),
            ),
        )
    )

    with pytest.raises(
        OpexSmartResolutionError,
    ) as exc_info:
        service().build_rows(
            budget=budget(),
            resolved=(
                reversed_distribution
            ),
            account_selection=(
                ACCOUNT_ADM_B
            ),
            cebe_selections={
                "04WF2EAF90":
                    CEBE_B,
            },
        )

    assert (
        exc_info.value.code
        == "DISTRIBUTION_MISMATCH"
    )
