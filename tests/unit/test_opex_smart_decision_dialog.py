import os
from dataclasses import replace
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QScrollArea

from app.models.opex_smart_import import (
    OpexSmartImportAccountChoice, OpexSmartImportCebeChoice,
    OpexSmartImportCebeDecision, OpexSmartImportCebeOption,
    OpexSmartImportDecision, OpexSmartImportPreparation, OpexSmartImportSheetReview,
)
from app.ui.dialogs.opex_smart_decision_dialog import OpexSmartDecisionDialog


pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def review_result():
    account = OpexSmartImportAccountChoice("SERVICIOS", "SOFTWARE", "GASTOS TI")
    cebe = OpexSmartImportCebeOption(
        "51IC000000", "TESORERIA", "CORPORATIVO", "TESORERIA", "LIMA", "SEDE A", "SEGMENTO",
    )
    review = OpexSmartImportSheetReview(
        "Licencias", (account, replace(account, categoria_gasto="EQUIPOS")),
        ("IMPORTE", "PORCENTAJE"),
        (OpexSmartImportCebeChoice(cebe.centro_beneficio, (cebe, replace(cebe, sede_cg="SEDE B"))),),
    )
    return OpexSmartImportPreparation(
        (), "plantilla.xlsx", 1, 0, Decimal("0"), (), (), (review,), (),
    )


def test_pending_controls_block_apply_until_every_selection_is_explicit(qapp):
    dialog = OpexSmartDecisionDialog(result=review_result())
    try:
        controls = dialog._controls["Licencias"]
        assert controls["account"].currentData() is None
        assert controls["cebes"]["51IC000000"].currentData() is None
        assert not dialog.save_button.isEnabled()
        assert "2 pendientes" in dialog.tabs.tabText(0)
        dialog._apply()
        assert dialog.overrides() == ()
        controls["account"].setCurrentIndex(2)
        assert not dialog.save_button.isEnabled()
        controls["cebes"]["51IC000000"].setCurrentIndex(2)
        assert dialog.save_button.isEnabled()
        assert "SEDE B" in controls["cebes"]["51IC000000"].toolTip()
        dialog._apply()
        chosen = dialog.overrides()[0]
        assert chosen.account.categoria_gasto == "EQUIPOS"
        assert chosen.cebe_selections[0].sede_cg == "SEDE B"
    finally:
        dialog.close()


def test_reopening_restores_complete_account_and_cebe_identity(qapp):
    result = review_result()
    selected = result.review_options[0].cebe_choices[0].options[1]
    decision = OpexSmartImportDecision(
        "Licencias", "SOFTWARE", "GASTOS TI", "PORCENTAJE",
        (OpexSmartImportCebeDecision(selected.centro_beneficio, selected.tipo_servicio_cg, selected),),
        categoria_gasto="EQUIPOS",
    )
    dialog = OpexSmartDecisionDialog(result=replace(result, decisions=(decision,)))
    try:
        controls = dialog._controls["Licencias"]
        assert controls["account"].currentData().categoria_gasto == "EQUIPOS"
        assert controls["cebes"][selected.centro_beneficio].currentData() == selected
        assert controls["distribution"].currentData() == "PORCENTAJE"
        assert dialog.save_button.isEnabled()
    finally:
        dialog.close()


def test_legacy_ambiguous_descriptions_do_not_select_first_alternative(qapp):
    result = review_result()
    decision = OpexSmartImportDecision(
        "Licencias", "SOFTWARE", "GASTOS TI", "IMPORTE",
        (OpexSmartImportCebeDecision("51IC000000", "TESORERIA"),),
    )
    dialog = OpexSmartDecisionDialog(result=replace(result, decisions=(decision,)))
    try:
        assert dialog._controls["Licencias"]["account"].currentData() is None
        assert dialog._controls["Licencias"]["cebes"]["51IC000000"].currentData() is None
        assert not dialog.save_button.isEnabled()
    finally:
        dialog.close()


def test_compact_dialog_keeps_details_accessible_by_scrolling(qapp):
    dialog = OpexSmartDecisionDialog(result=review_result())
    try:
        dialog.resize(720, 520)
        controls = dialog._controls["Licencias"]
        controls["account"].setCurrentIndex(1)
        controls["cebes"]["51IC000000"].setCurrentIndex(2)
        dialog.grab()
        qapp.processEvents()
        scroll = dialog.findChild(QScrollArea)
        assert scroll.verticalScrollBar().maximum() > 0
        scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
        dialog.grab()
        detail = next(label for label in scroll.findChildren(QLabel) if "Segmentación:" in label.text())
        assert detail.height() >= detail.heightForWidth(detail.width())
        assert dialog.save_button.isEnabled()
    finally:
        dialog.close()
