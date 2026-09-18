from dataclasses import replace
from decimal import Decimal

import pytest

from app.models.opex_master_data import (
    OpexAccountMasterRecord,
    OpexMasterDataSnapshot,
    OpexMasterSource,
)
from app.models.opex_smart_resolution_plan import OpexSmartResolutionPlanIssue
from app.models.opex_smart_template import OpexTemplateBudget, OpexTemplateDistribution
from app.services.opex_smart_default_resolution_service import (
    OpexSmartDefaultResolutionError,
    OpexSmartDefaultResolutionService,
)
from app.services.opex_smart_import_preparation_service import (
    OpexSmartImportPreparationService,
)
from app.ui.workers.opex_smart_import_worker import OpexSmartImportWorker


pytestmark = pytest.mark.unit


def missing_recoverables_state():
    source = OpexMasterSource(
        path="test.xlsx", sheet_name="Sheet1", header_row=1,
        physical_rows=1, unique_rows=1, duplicate_rows=0,
    )
    account = OpexAccountMasterRecord(
        numero_cuenta="600000001", categoria_gasto="SERVICIOS",
        nombre_cuenta="CUENTA TEST", atributo_2="GASTOS TI",
    )
    snapshot = OpexMasterDataSnapshot(
        accounts={account.numero_cuenta: account}, cebes={}, recoverables={},
        account_conflicts={}, cebe_conflicts={}, recoverable_conflicts={},
        account_source=source, cebe_source=source, recoverable_source=source,
    )
    budget = OpexTemplateBudget(
        sheet_name="Licencias", nombre_gasto="Licencias de software",
        proveedor="Proveedor", moneda_facturacion="USD",
        numero_cuenta=account.numero_cuenta, tipo="MENSUAL", monto=Decimal("100"),
        distributions=tuple(
            OpexTemplateDistribution(
                excel_row=row, ceco=ceco, percentage=None, amount=Decimal("1"),
            )
            for row, ceco in ((8, "60BK000004"), (9, "62BD000004"))
        ),
    )
    manager = OpexSmartImportPreparationService._build_state_service(snapshot)
    return manager, manager.create_budget_state(budget)


def test_plan_preserves_excel_location_for_each_missing_recoverable():
    manager, state = missing_recoverables_state()
    issues = manager.plan(state).issues

    assert [(issue.code, issue.excel_row, issue.ceco) for issue in issues] == [
        ("RECOVERABLE_NOT_FOUND", 8, "60BK000004"),
        ("RECOVERABLE_NOT_FOUND", 9, "62BD000004"),
    ]


def test_default_resolution_error_exposes_both_cecos_and_sheet():
    manager, state = missing_recoverables_state()

    with pytest.raises(OpexSmartDefaultResolutionError) as caught:
        OpexSmartDefaultResolutionService(state_service=manager).apply_budget_defaults(state)

    error = caught.value
    assert error.sheet_name == "Licencias"
    assert len(error.issues) == 2
    assert 'La hoja "Licencias"' in str(error)
    assert "Fila Excel 8 | CECO 60BK000004" in str(error)
    assert "Fila Excel 9 | CECO 62BD000004" in str(error)
    assert "RECOVERABLE_NOT_FOUND" in str(error)
    assert "RECUPERABLES.xlsx" in str(error)


def test_worker_forwards_business_context_without_successful_import():
    manager, state = missing_recoverables_state()

    class FailingPreparation:
        def prepare(self, **kwargs):
            return OpexSmartDefaultResolutionService(
                state_service=manager,
            ).apply_budget_defaults(state)

    worker = OpexSmartImportWorker(
        service=FailingPreparation(), source_path="plantilla.xlsx",
        origin="PB", budgeter="TEST", actor="tester",
    )
    succeeded, failed = [], []
    worker.succeeded.connect(succeeded.append)
    worker.failed.connect(failed.append)
    worker.run()

    assert succeeded == []
    assert len(failed) == 1
    assert "Licencias" in failed[0]
    assert "Fila Excel 8 | CECO 60BK000004" in failed[0]
    assert "Fila Excel 9 | CECO 62BD000004" in failed[0]


def test_large_diagnostic_keeps_all_issues_and_limits_preview():
    issue = OpexSmartResolutionPlanIssue(
        code="RECOVERABLE_NOT_FOUND", message="Revisa RECUPERABLES.xlsx.",
    )
    issues = tuple(
        replace(issue, excel_row=8 + index, ceco=f"CECO{index}")
        for index in range(7)
    )
    error = OpexSmartDefaultResolutionService._blocking_error("Licencias", issues)

    assert error.issues == issues
    assert "7 incidencias bloqueantes" in str(error)
    assert "CECO4" in str(error)
    assert "CECO5" not in str(error)
    assert "2 incidencias adicionales" in str(error)


def test_budget_level_issue_does_not_invent_a_ceco_or_excel_row():
    issue = OpexSmartResolutionPlanIssue(
        code="ACCOUNT_NOT_FOUND", message="La cuenta no existe en CUENTA.xlsx.",
        key="600000099",
    )
    error = OpexSmartDefaultResolutionService._blocking_error("Licencias", (issue,))

    assert "Referencia 600000099" in str(error)
    assert "CUENTA.xlsx" in str(error)
    assert "Fila Excel" not in str(error)
    assert "CECO" not in str(error)
