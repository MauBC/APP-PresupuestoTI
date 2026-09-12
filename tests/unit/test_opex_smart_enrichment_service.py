from decimal import Decimal

import pytest

from app.models.opex_master_data import (
    OpexAccountMasterRecord,
    OpexCebeMasterRecord,
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
    OpexSmartEnrichmentBuildError,
    OpexSmartEnrichmentService,
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


def snapshot():
    return OpexMasterDataSnapshot(
        accounts={
            "600000001": OpexAccountMasterRecord(
                numero_cuenta="600000001",
                categoria_gasto="SERVICIOS",
                nombre_cuenta="CUENTA TEST",
                atributo_2="ATRIBUTO",
            ),
        },
        cebes={
            "04WF2EAF90": OpexCebeMasterRecord(
                centro_beneficio="04WF2EAF90",
                desc_cebe="CEBE 04",
                macroservicio_cg="MACRO",
                tipo_servicio_cg="TIPO",
                region_cg="REGION",
                sede_cg="SEDE",
                segmentacion="SEG",
            ),
            "291ACC9900": OpexCebeMasterRecord(
                centro_beneficio="291ACC9900",
                desc_cebe="CEBE 291",
                macroservicio_cg="MACRO",
                tipo_servicio_cg="TIPO",
                region_cg="REGION",
                sede_cg="SEDE",
                segmentacion="SEG",
            ),
        },
        recoverables={
            "4": OpexRecoverableMasterRecord(
                inicial="4",
                sociedad="2504",
                compania="Colombia Almacenes",
                pais="CO",
            ),
            "291": OpexRecoverableMasterRecord(
                inicial="291",
                sociedad="291",
                compania="Alma Peru",
                pais="PE",
            ),
        },
        account_conflicts={},
        cebe_conflicts={},
        recoverable_conflicts={},
        account_source=SOURCE,
        cebe_source=SOURCE,
        recoverable_source=SOURCE,
    )


def service():
    return OpexSmartEnrichmentService(
        OpexMasterEnrichmentService(snapshot())
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
                percentage=Decimal("0.40"),
                amount=Decimal("400"),
            ),
            OpexTemplateDistribution(
                excel_row=9,
                ceco="291ACC9904",
                percentage=Decimal("0.60"),
                amount=Decimal("600"),
            ),
        ),
    )


def test_analyze_budget_enriches_all_cecos():
    result = service().analyze_budget(budget())

    assert not result.issues
    assert len(result.drafts) == 2

    assert (
        result.drafts[0].enrichment.compania
        == "Colombia Almacenes"
    )

    assert (
        result.drafts[1].enrichment.compania
        == "Alma Peru"
    )


def test_analysis_keeps_distribution_status():
    result = service().analyze_budget(budget())

    assert result.distribution_status.percentage_valid
    assert result.distribution_status.amount_valid


def test_master_error_is_contextual_and_does_not_abort_analysis():
    invalid = OpexTemplateBudget(
        sheet_name="Gasto malo",
        nombre_gasto="SERVICIO",
        proveedor="P",
        moneda_facturacion="USD",
        numero_cuenta="600000001",
        tipo="ANUAL",
        monto=Decimal("100"),
        distributions=(
            OpexTemplateDistribution(
                excel_row=8,
                ceco="04WF2EAF93",
                percentage=Decimal("0.50"),
                amount=Decimal("50"),
            ),
            OpexTemplateDistribution(
                excel_row=9,
                ceco="999ABC0004",
                percentage=Decimal("0.50"),
                amount=Decimal("50"),
            ),
        ),
    )

    result = service().analyze_budget(invalid)

    assert len(result.drafts) == 1
    assert len(result.issues) == 1

    issue = result.issues[0]

    assert issue.excel_row == 9
    assert issue.ceco == "999ABC0004"

    assert issue.code in {
        "RECOVERABLE_NOT_FOUND",
        "CEBE_NOT_FOUND",
    }


def test_build_rows_uses_resolved_amounts():
    resolved = OpexTemplateResolvedDistribution(
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

    rows = service().build_rows(
        budget=budget(),
        resolved=resolved,
    )

    assert len(rows) == 2

    assert rows[0].monto_ceco == Decimal("400.00")
    assert rows[1].monto_ceco == Decimal("600.00")

    assert (
        sum(
            row.monto_ceco
            for row in rows
        )
        == Decimal("1000.00")
    )


def test_build_rows_rejects_missing_ceco():
    resolved = OpexTemplateResolvedDistribution(
        mode="IMPORTE",
        amounts=(
            (
                "04WF2EAF93",
                Decimal("1000"),
            ),
        ),
    )

    with pytest.raises(
        OpexSmartEnrichmentBuildError,
        match="no coincide",
    ):
        service().build_rows(
            budget=budget(),
            resolved=resolved,
        )


def test_workbook_analysis_preserves_source():
    workbook = OpexSmartTemplateWorkbook(
        source_path="demo.xlsx",
        budgets=(
            budget(),
        ),
    )

    result = service().analyze_workbook(workbook)

    assert result.source_path == "demo.xlsx"
    assert len(result.budgets) == 1

def test_ambiguous_account_is_budget_issue_not_one_issue_per_ceco():
    base = snapshot()

    option_a = (
        OpexAccountMasterRecord(
            numero_cuenta="600000001",
            categoria_gasto="EQUIPO",
            nombre_cuenta="ADM",
            atributo_2="A",
        )
    )

    option_b = (
        OpexAccountMasterRecord(
            numero_cuenta="600000001",
            categoria_gasto="EQUIPO",
            nombre_cuenta="VTAS",
            atributo_2="B",
        )
    )

    from app.models.opex_master_data import (
        OpexMasterConflict,
    )

    ambiguous = (
        OpexMasterDataSnapshot(
            accounts={},
            cebes=base.cebes,
            recoverables=(
                base.recoverables
            ),
            account_conflicts={
                "600000001": (
                    OpexMasterConflict(
                        key="600000001",
                        locations=(
                            "Sheet1:2",
                            "Sheet1:3",
                        ),
                        records=(
                            option_a,
                            option_b,
                        ),
                    )
                )
            },
            cebe_conflicts={},
            recoverable_conflicts={},
            account_source=SOURCE,
            cebe_source=SOURCE,
            recoverable_source=SOURCE,
        )
    )

    smart = (
        OpexSmartEnrichmentService(
            OpexMasterEnrichmentService(
                ambiguous
            )
        )
    )

    result = smart.analyze_budget(
        budget()
    )

    assert len(
        result.budget_issues
    ) == 1

    assert (
        result.budget_issues[0].code
        == "ACCOUNT_AMBIGUOUS"
    )

    assert len(
        result.account_options
    ) == 2

    assert len(
        result.drafts
    ) == 2

    assert not result.issues


def test_ceco_problem_remains_row_level_when_account_is_ambiguous():
    base = snapshot()

    from app.models.opex_master_data import (
        OpexMasterConflict,
    )

    account_a = valid_account = (
        OpexAccountMasterRecord(
            numero_cuenta="600000001",
            categoria_gasto="EQUIPO",
            nombre_cuenta="ADM",
            atributo_2="A",
        )
    )

    account_b = (
        OpexAccountMasterRecord(
            numero_cuenta="600000001",
            categoria_gasto="EQUIPO",
            nombre_cuenta="VTAS",
            atributo_2="B",
        )
    )

    cebe_a = (
        OpexCebeMasterRecord(
            centro_beneficio=(
                "04WF2EAF90"
            ),
            desc_cebe="A",
            macroservicio_cg="MACRO",
            tipo_servicio_cg="TIPO",
            region_cg="REGION",
            sede_cg="SEDE",
            segmentacion="SEG",
        )
    )

    cebe_b = (
        OpexCebeMasterRecord(
            centro_beneficio=(
                "04WF2EAF90"
            ),
            desc_cebe="B",
            macroservicio_cg="MACRO",
            tipo_servicio_cg="TIPO",
            region_cg="REGION",
            sede_cg="SEDE",
            segmentacion="SEG",
        )
    )

    ambiguous = (
        OpexMasterDataSnapshot(
            accounts={},
            cebes={
                "291ACC9900":
                    base.cebes[
                        "291ACC9900"
                    ],
            },
            recoverables=(
                base.recoverables
            ),
            account_conflicts={
                "600000001": (
                    OpexMasterConflict(
                        key="600000001",
                        locations=(
                            "A",
                            "B",
                        ),
                        records=(
                            account_a,
                            account_b,
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
                            cebe_a,
                            cebe_b,
                        ),
                    )
                )
            },
            recoverable_conflicts={},
            account_source=SOURCE,
            cebe_source=SOURCE,
            recoverable_source=SOURCE,
        )
    )

    smart = (
        OpexSmartEnrichmentService(
            OpexMasterEnrichmentService(
                ambiguous
            )
        )
    )

    result = smart.analyze_budget(
        budget()
    )

    assert len(
        result.budget_issues
    ) == 1

    assert len(
        result.drafts
    ) == 1

    assert len(
        result.issues
    ) == 1

    assert (
        result.issues[0].code
        == "CEBE_AMBIGUOUS"
    )
