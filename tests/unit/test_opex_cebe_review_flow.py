from dataclasses import replace
from decimal import Decimal

import pytest

from app.models.opex_fx import OpexFxTable
from app.models.opex_master_data import (
    OpexAccountMasterRecord, OpexCebeMasterRecord, OpexMasterConflict,
    OpexMasterDataSnapshot, OpexMasterSource, OpexRecoverableMasterRecord,
)
from app.models.opex_smart_import import OpexSmartImportSheetOverride
from app.models.opex_smart_template import (
    OpexSmartTemplateWorkbook, OpexTemplateBudget, OpexTemplateDistribution,
)
from app.services import opex_smart_import_preparation_service as preparation


pytestmark = pytest.mark.unit


def test_ambiguous_cebe_requires_review_before_rows_can_be_generated(tmp_path, monkeypatch):
    source = tmp_path / "plantilla.xlsx"
    source.touch()
    account = OpexAccountMasterRecord("600000001", "SERVICIOS", "SOFTWARE", "GASTOS TI")
    first = OpexCebeMasterRecord(
        "51IC000000", "TESORERIA", "CORPORATIVO", "TESORERIA", "LIMA", "SEDE A", "SEGMENTO",
    )
    second = replace(first, sede_cg="SEDE B")
    metadata = OpexMasterSource("test.xlsx", "Sheet1", 1, 2, 2, 0)
    snapshot = OpexMasterDataSnapshot(
        accounts={account.numero_cuenta: account}, cebes={},
        recoverables={"51": OpexRecoverableMasterRecord("51", "2501", "EMPRESA", "PE")},
        account_conflicts={}, recoverable_conflicts={},
        cebe_conflicts={first.centro_beneficio: OpexMasterConflict(
            first.centro_beneficio, ("Sheet1:2", "Sheet1:3"), (first, second),
        )},
        account_source=metadata, cebe_source=metadata, recoverable_source=metadata,
    )
    budget = OpexTemplateBudget(
        "Licencias", "Software", "Proveedor", "USD", account.numero_cuenta,
        "MENSUAL", Decimal("100"),
        (OpexTemplateDistribution(8, "51IC000002", None, Decimal("1")),),
    )
    workbook = OpexSmartTemplateWorkbook(str(source), (budget,))
    monkeypatch.setattr(preparation.OpexSmartTemplateLoader, "load", lambda self, path: workbook)
    monkeypatch.setattr(preparation.OpexMasterDataLoader, "load", lambda self: snapshot)
    fx_calls = []

    def load_fx(self, path):
        fx_calls.append(path)
        return OpexFxTable(2027, {"USD": Decimal("1"), "PEN": Decimal("3.40")}, {"PE": "PEN"})

    monkeypatch.setattr(preparation.OpexFxLoader, "load", load_fx)
    service = preparation.OpexSmartImportPreparationService(tmp_path)
    request = dict(source_path=source, origin="PB", budgeter="TEST", actor="tester")
    pending = service.prepare(**request)

    assert pending.rows == ()
    assert fx_calls == []
    assert pending.decisions[0].cebe_decisions == ()
    assert pending.decisions[0].categoria_gasto == account.categoria_gasto
    review = pending.review_options[0]
    selected = review.cebe_choices[0].options[1]

    ready = service.prepare(**request, overrides=(OpexSmartImportSheetOverride(
        "Licencias", account=review.account_options[0], distribution_mode="IMPORTE",
        cebe_selections=(selected,),
    ),))

    assert len(ready.rows) == 1
    assert ready.rows[0]["sede_cg"] == "SEDE B"
    assert ready.total_usd == Decimal("1200")
    assert ready.decisions[0].cebe_decisions[0].selected_option == selected
    assert len(fx_calls) == 1
