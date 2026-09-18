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
    OpexSmartTemplateWorkbook,
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
from app.services.opex_smart_resolution_state_service import (
    OpexSmartResolutionStateError,
    OpexSmartResolutionStateService,
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
    desc_cebe="CEBE",
    macroservicio_cg="MACRO",
    tipo_servicio_cg="TIPO A",
    region_cg="REGION",
    sede_cg="SEDE",
    segmentacion="SEG",
)

CEBE_B = OpexCebeMasterRecord(
    centro_beneficio="04WF2EAF90",
    desc_cebe="CEBE",
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


def budget(
    sheet_name="Gasto 1",
):
    return OpexTemplateBudget(
        sheet_name=sheet_name,
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


def service():
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

    plan = (
        OpexSmartResolutionPlanService(
            analysis_service=analysis,
            resolution_service=resolution,
        )
    )

    return (
        OpexSmartResolutionStateService(
            plan_service=plan,
            resolution_service=resolution,
        )
    )


def complete_state():
    current = (
        service()
        .create_budget_state(
            budget()
        )
    )

    current.account_selection = (
        ACCOUNT_A
    )

    current.cebe_selections[
        "04WF2EAF90"
    ] = CEBE_B

    current.resolved_distribution = (
        resolved()
    )

    return current


def test_initial_state_is_pending():
    current = (
        service()
        .create_budget_state(
            budget()
        )
    )

    plan = (
        service()
        .plan(
            current
        )
    )

    assert not plan.ready
    assert not plan.account_resolved
    assert not plan.cebe_resolved
    assert not plan.distribution_resolved


def test_select_account_uses_official_record():
    manager = service()

    current = (
        manager
        .create_budget_state(
            budget()
        )
    )

    selected = (
        manager
        .select_account(
            current,
            categoria_gasto="Equipo",
            nombre_cuenta="SOFTWARE ADM",
            atributo_2="A",
        )
    )

    assert selected == ACCOUNT_A
    assert (
        current.account_selection
        == ACCOUNT_A
    )


def test_select_cebe_uses_official_option():
    manager = service()

    current = (
        manager
        .create_budget_state(
            budget()
        )
    )

    manager.select_cebe(
        current,
        "04WF2EAF90",
        CEBE_B,
    )

    assert (
        current.cebe_selections[
            "04WF2EAF90"
        ]
        == CEBE_B
    )


def test_select_cebe_rejects_foreign_record():
    manager = service()

    current = (
        manager
        .create_budget_state(
            budget()
        )
    )

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

    with pytest.raises(
        OpexSmartResolutionStateError,
    ) as exc_info:
        manager.select_cebe(
            current,
            "04WF2EAF90",
            foreign,
        )

    assert (
        exc_info.value.code
        == "CEBE_SELECTION_INVALID"
    )


def test_state_becomes_ready_after_all_choices():
    manager = service()

    current = (
        manager
        .create_budget_state(
            budget()
        )
    )

    manager.select_account(
        current,
        categoria_gasto="Equipo",
        nombre_cuenta="SOFTWARE ADM",
        atributo_2="A",
    )

    manager.select_cebe(
        current,
        "04WF2EAF90",
        CEBE_B,
    )

    manager.set_distribution(
        current,
        resolved(),
    )

    plan = manager.plan(
        current
    )

    assert plan.ready


def test_clear_selection_returns_to_pending():
    manager = service()

    current = complete_state()

    assert (
        manager.plan(
            current
        ).ready
    )

    manager.clear_cebe(
        current,
        "04WF2EAF90",
    )

    assert not (
        manager.plan(
            current
        ).ready
    )


def test_build_rows_blocks_pending_state():
    manager = service()

    current = (
        manager
        .create_budget_state(
            budget()
        )
    )

    with pytest.raises(
        OpexSmartResolutionStateError,
    ) as exc_info:
        manager.build_rows(
            current
        )

    assert (
        exc_info.value.code
        == "RESOLUTION_NOT_READY"
    )


def test_build_rows_returns_final_enriched_rows():
    manager = service()

    current = complete_state()

    rows = manager.build_rows(
        current
    )

    assert len(rows) == 1

    row = rows[0]

    assert row.monto_ceco == Decimal("1000")
    assert (
        row.enrichment.nombre_cuenta
        == "SOFTWARE ADM"
    )
    assert (
        row.enrichment.tipo_servicio_cg
        == "TIPO B"
    )


def test_workbook_states_are_independent():
    manager = service()

    workbook = (
        OpexSmartTemplateWorkbook(
            source_path="demo.xlsx",
            budgets=(
                budget("Sheet A"),
                budget("Sheet B"),
            ),
        )
    )

    state = (
        manager
        .create_workbook_state(
            workbook
        )
    )

    sheet_a = (
        manager.get_budget_state(
            state,
            "Sheet A",
        )
    )

    sheet_b = (
        manager.get_budget_state(
            state,
            "Sheet B",
        )
    )

    manager.select_account(
        sheet_a,
        categoria_gasto="Equipo",
        nombre_cuenta="SOFTWARE ADM",
        atributo_2="A",
    )

    assert (
        sheet_a.account_selection
        == ACCOUNT_A
    )

    assert (
        sheet_b.account_selection
        is None
    )

    assert not (
        manager.workbook_ready(
            state
        )
    )
