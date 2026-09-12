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
from app.services.opex_smart_enrichment_service import (
    OpexSmartEnrichmentService,
)
from app.services.opex_smart_resolution_plan_service import (
    OpexSmartResolutionPlanService,
)
from app.services.opex_smart_resolution_service import (
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


ACCOUNT_A = OpexAccountMasterRecord(
    numero_cuenta="600000001",
    categoria_gasto="Equipo",
    nombre_cuenta="SOFTWARE ADM",
    atributo_2="A",
)

ACCOUNT_B = OpexAccountMasterRecord(
    numero_cuenta="600000001",
    categoria_gasto="Equipo",
    nombre_cuenta="SOFTWARE VTAS",
    atributo_2="B",
)


CEBE_A = OpexCebeMasterRecord(
    centro_beneficio="04WF2EAF90",
    desc_cebe="CEBE A",
    macroservicio_cg="MACRO",
    tipo_servicio_cg="TIPO A",
    region_cg="REGION",
    sede_cg="SEDE",
    segmentacion="SEG",
)

CEBE_B = OpexCebeMasterRecord(
    centro_beneficio="04WF2EAF90",
    desc_cebe="CEBE A",
    macroservicio_cg="MACRO",
    tipo_servicio_cg="TIPO B",
    region_cg="REGION",
    sede_cg="SEDE",
    segmentacion="SEG",
)


def snapshot():
    return OpexMasterDataSnapshot(
        accounts={},
        cebes={},
        recoverables={
            "4": (
                OpexRecoverableMasterRecord(
                    inicial="4",
                    sociedad="2504",
                    compania="Colombia",
                    pais="CO",
                )
            ),
        },
        account_conflicts={
            "600000001": (
                OpexMasterConflict(
                    key="600000001",
                    locations=("A", "B"),
                    records=(
                        ACCOUNT_A,
                        ACCOUNT_B,
                    ),
                )
            )
        },
        cebe_conflicts={
            "04WF2EAF90": (
                OpexMasterConflict(
                    key="04WF2EAF90",
                    locations=("A", "B"),
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


def budget():
    return OpexTemplateBudget(
        sheet_name="Gasto 1",
        nombre_gasto="SERVICIO",
        proveedor="PROVEEDOR",
        moneda_facturacion="USD",
        numero_cuenta="600000001",
        tipo="ANUAL",
        monto=Decimal("1000"),
        distributions=(
            OpexTemplateDistribution(
                excel_row=8,
                ceco="04WF2EAF93",
                percentage=Decimal("1"),
                amount=Decimal("1000"),
            ),
        ),
    )


def resolved():
    return OpexTemplateResolvedDistribution(
        mode="IMPORTE",
        amounts=(
            (
                "04WF2EAF93",
                Decimal("1000"),
            ),
        ),
    )


def plan_service():
    master = (
        OpexMasterEnrichmentService(
            snapshot()
        )
    )

    analysis = (
        OpexSmartEnrichmentService(
            master
        )
    )

    resolution = (
        OpexSmartResolutionService(
            master
        )
    )

    return (
        OpexSmartResolutionPlanService(
            analysis_service=analysis,
            resolution_service=resolution,
        )
    )


def test_plan_starts_pending():
    plan = (
        plan_service()
        .build_plan(
            budget()
        )
    )

    assert not plan.ready
    assert not plan.account_resolved
    assert not plan.cebe_resolved
    assert not plan.distribution_resolved

    assert (
        plan.unresolved_cebes
        == ("04WF2EAF90",)
    )


def test_account_selection_resolves_only_account():
    plan = (
        plan_service()
        .build_plan(
            budget(),
            account_selection=(
                ACCOUNT_A
            ),
        )
    )

    assert plan.account_resolved
    assert not plan.cebe_resolved
    assert not plan.distribution_resolved
    assert not plan.ready


def test_cebe_selection_resolves_cebe():
    plan = (
        plan_service()
        .build_plan(
            budget(),
            account_selection=(
                ACCOUNT_A
            ),
            cebe_selections={
                "04WF2EAF90":
                    CEBE_B,
            },
        )
    )

    assert plan.account_resolved
    assert plan.cebe_resolved
    assert not plan.distribution_resolved
    assert not plan.ready


def test_full_plan_becomes_ready():
    plan = (
        plan_service()
        .build_plan(
            budget(),
            account_selection=(
                ACCOUNT_A
            ),
            cebe_selections={
                "04WF2EAF90":
                    CEBE_B,
            },
            resolved_distribution=(
                resolved()
            ),
        )
    )

    assert plan.account_resolved
    assert plan.cebe_resolved
    assert plan.distribution_resolved
    assert not plan.issues
    assert plan.ready


def test_wrong_distribution_total_blocks_ready():
    invalid = (
        OpexTemplateResolvedDistribution(
            mode="IMPORTE",
            amounts=(
                (
                    "04WF2EAF93",
                    Decimal("900"),
                ),
            ),
        )
    )

    plan = (
        plan_service()
        .build_plan(
            budget(),
            account_selection=(
                ACCOUNT_A
            ),
            cebe_selections={
                "04WF2EAF90":
                    CEBE_B,
            },
            resolved_distribution=(
                invalid
            ),
        )
    )

    assert not plan.ready
    assert not plan.distribution_resolved

    assert any(
        issue.code
        == "DISTRIBUTION_TOTAL_MISMATCH"
        for issue in plan.issues
    )


def test_foreign_cebe_selection_blocks_ready():
    foreign = (
        OpexCebeMasterRecord(
            centro_beneficio="04WF2EAF90",
            desc_cebe="INVENTADO",
            macroservicio_cg="X",
            tipo_servicio_cg="X",
            region_cg="X",
            sede_cg="X",
            segmentacion="X",
        )
    )

    plan = (
        plan_service()
        .build_plan(
            budget(),
            account_selection=(
                ACCOUNT_A
            ),
            cebe_selections={
                "04WF2EAF90":
                    foreign,
            },
            resolved_distribution=(
                resolved()
            ),
        )
    )

    assert not plan.ready
    assert not plan.cebe_resolved

    assert any(
        issue.code
        == "CEBE_SELECTION_INVALID"
        for issue in plan.issues
    )
