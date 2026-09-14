from decimal import Decimal

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.repositories.presupuesto_repository import (
    PresupuestoRepository,
)
from app.ui.dialogs.history_detail_dialog import (
    format_audit_display,
    format_audit_field,
)


pytestmark = pytest.mark.unit


class FakeBigQuery:
    pass


def _repository(
    module_config,
    row,
):
    repository = PresupuestoRepository(
        FakeBigQuery(),
        module_config=module_config,
    )

    repository.get_rows_by_ids = (
        lambda row_ids: (
            dict(row),
        )
    )

    return repository


def test_opex_history_context_uses_business_columns():
    row = {
        "row_id": "opex-1",
        "presupuestador": "Sandra",
        "pais": "PE",
        "compania": "Ransa",
        "proveedor": "Microsoft",
        "nombre_gasto": "Azure",
        "ceco": "001234",
        "enero_usd": Decimal("100"),
    }

    repository = _repository(
        OPEX_MODULE_CONFIG,
        row,
    )

    result = (
        repository
        .get_history_row_context(
            ("opex-1",)
        )
    )

    assert len(result) == 1

    context = result[0]

    assert (
        tuple(context)
        ==
        (
            "row_id",
            *OPEX_MODULE_CONFIG
            .change_detail_columns,
        )
    )

    assert context["row_id"] == "opex-1"
    assert context["proveedor"] == "Microsoft"
    assert context["nombre_gasto"] == "Azure"

    assert "enero_usd" not in context


def test_capex_history_context_uses_business_columns():
    row = {
        "row_id": "capex-1",
        "presupuestador": "Mauro",
        "responsable": "Responsable Uno",
        "pais": "PE",
        "sociedad": "2501",
        "nombre_inversion": "Proyecto Data",
        "tipo_capex": "TI",
        "codigo_cebe": "04WF2EAF90",
        "codigo_ceco": "04WF2EAF93",
    }

    repository = _repository(
        CAPEX_MODULE_CONFIG,
        row,
    )

    result = (
        repository
        .get_history_row_context(
            ("capex-1",)
        )
    )

    context = result[0]

    assert (
        context["nombre_inversion"]
        == "Proyecto Data"
    )

    assert (
        context["codigo_cebe"]
        == "04WF2EAF90"
    )

    assert (
        context["codigo_ceco"]
        == "04WF2EAF93"
    )


def test_history_formats_usd():
    assert (
        format_audit_display(
            "1234.5",
            "NUMERIC",
            "enero_usd",
        )
        == "US$ 1,234.50"
    )


def test_history_formats_ml():
    assert (
        format_audit_display(
            "1234.5",
            "NUMERIC",
            "enero_ml",
        )
        == "ML 1,234.50"
    )


def test_history_formats_mf():
    assert (
        format_audit_display(
            "45.25",
            "NUMERIC",
            "enero_mf",
        )
        == "MF 45.25"
    )


def test_history_formats_boolean_state():
    assert (
        format_audit_display(
            "true",
            "BOOLEAN",
            "habilitado",
        )
        == "Habilitado"
    )

    assert (
        format_audit_display(
            "false",
            "BOOLEAN",
            "habilitado",
        )
        == "Deshabilitado"
    )


def test_history_field_uses_shared_labels():
    assert (
        format_audit_field(
            "codigo_ceco"
        )
        == "Codigo CECO"
    )

    assert (
        format_audit_field(
            "anio_usd"
        )
        == "Total Anual USD"
    )
