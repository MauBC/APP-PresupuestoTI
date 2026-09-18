import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
)
from app.services.opex_smart_inference_service import (
    OpexSmartInferenceError,
    OpexSmartInferenceService,
)


pytestmark = pytest.mark.unit


def make_row(
    *,
    ceco="001234",
    pais="PER",
    nombre_gasto="LICENCIAS",
    categoria_gasto="SOFTWARE",
    proveedor="MICROSOFT",
    presupuestador="ANA",
    moneda_facturacion="USD",
    periodo="2026",
    enabled=True,
):
    return {
        "ceco": ceco,
        "pais": pais,
        "nombre_gasto":
            nombre_gasto,
        "categoria_gasto":
            categoria_gasto,
        "proveedor": proveedor,
        "presupuestador":
            presupuestador,
        "moneda_facturacion":
            moneda_facturacion,
        "periodo": periodo,
        "habilitado": enabled,
    }


def test_combined_context_autocompletes_unique_values():
    service = (
        OpexSmartInferenceService()
    )

    rows = (
        make_row(
            ceco="001234",
            proveedor="MICROSOFT",
        ),
        make_row(
            ceco="009999",
            proveedor="OTRO",
        ),
    )

    result = service.infer(
        {
            "nombre_gasto":
                "LICENCIAS",
            "ceco":
                "001234",
        },
        rows,
    )

    values = (
        result.resolved_values
    )

    assert (
        result.matching_row_count
        == 1
    )

    assert (
        values["pais"]
        == "PER"
    )

    assert (
        values["categoria_gasto"]
        == "SOFTWARE"
    )

    assert (
        values["proveedor"]
        == "MICROSOFT"
    )


def test_ambiguous_values_are_not_autocompleted():
    service = (
        OpexSmartInferenceService()
    )

    rows = (
        make_row(
            proveedor="MICROSOFT",
        ),
        make_row(
            proveedor="ORACLE",
        ),
    )

    result = service.infer(
        {
            "nombre_gasto":
                "LICENCIAS",
        },
        rows,
    )

    assert (
        "proveedor"
        not in result
        .resolved_values
    )

    assert (
        result
        .ambiguous_map[
            "proveedor"
        ]
        == (
            "MICROSOFT",
            "ORACLE",
        )
    )

    assert (
        result
        .resolved_values[
            "categoria_gasto"
        ]
        == "SOFTWARE"
    )


def test_combined_filters_resolve_previous_ambiguity():
    service = (
        OpexSmartInferenceService()
    )

    rows = (
        make_row(
            ceco="001234",
            proveedor="MICROSOFT",
        ),
        make_row(
            ceco="009999",
            proveedor="ORACLE",
        ),
    )

    broad = service.infer(
        {
            "nombre_gasto":
                "LICENCIAS",
        },
        rows,
    )

    assert (
        "proveedor"
        in broad.ambiguous_map
    )

    narrowed = service.infer(
        {
            "nombre_gasto":
                "LICENCIAS",
            "ceco":
                "001234",
        },
        rows,
    )

    assert (
        narrowed
        .resolved_values[
            "proveedor"
        ]
        == "MICROSOFT"
    )


def test_explicit_values_are_never_replaced():
    service = (
        OpexSmartInferenceService()
    )

    result = service.infer(
        {
            "nombre_gasto":
                "LICENCIAS",
            "proveedor":
                "MICROSOFT",
        },
        (
            make_row(),
        ),
    )

    assert (
        result.resolved_values[
            "proveedor"
        ]
        == "MICROSOFT"
    )

    assert (
        "proveedor"
        not in dict(
            result.inferred_values
        )
    )


def test_no_history_returns_no_data_without_guessing():
    service = (
        OpexSmartInferenceService()
    )

    result = service.infer(
        {
            "nombre_gasto":
                "GASTO NUEVO",
        },
        (
            make_row(),
        ),
    )

    assert not (
        result.has_historical_match
    )

    assert (
        result.matching_row_count
        == 0
    )

    assert (
        result.resolved_values
        == {
            "nombre_gasto":
                "GASTO NUEVO",
        }
    )

    assert (
        "proveedor"
        in result.no_data_columns
    )


def test_disabled_history_is_ignored():
    service = (
        OpexSmartInferenceService()
    )

    rows = (
        make_row(
            proveedor="ACTIVO",
        ),
        make_row(
            proveedor="ANTIGUO",
            enabled=False,
        ),
    )

    result = service.infer(
        {
            "nombre_gasto":
                "LICENCIAS",
        },
        rows,
    )

    assert (
        result.resolved_values[
            "proveedor"
        ]
        == "ACTIVO"
    )


def test_leading_zero_codes_are_preserved():
    service = (
        OpexSmartInferenceService()
    )

    result = service.infer(
        {
            "nombre_gasto":
                "LICENCIAS",
        },
        (
            make_row(
                ceco="001234",
            ),
        ),
    )

    assert (
        result.resolved_values[
            "ceco"
        ]
        == "001234"
    )


def test_invalid_dimension_is_rejected():
    service = (
        OpexSmartInferenceService()
    )

    with pytest.raises(
        OpexSmartInferenceError,
        match="no validas",
    ):
        service.infer(
            {
                "columna_inventada":
                    "X",
            },
            (
                make_row(),
            ),
        )


def test_blank_context_is_rejected():
    service = (
        OpexSmartInferenceService()
    )

    with pytest.raises(
        OpexSmartInferenceError,
        match="al menos un dato",
    ):
        service.infer(
            {
                "nombre_gasto":
                    "   ",
            },
            (
                make_row(),
            ),
        )


def test_capex_config_is_rejected():
    with pytest.raises(
        OpexSmartInferenceError,
        match="solo admite OPEX",
    ):
        OpexSmartInferenceService(
            CAPEX_MODULE_CONFIG
        )
