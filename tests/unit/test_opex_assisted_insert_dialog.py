from types import SimpleNamespace

import pytest

from app.ui.dialogs.opex_assisted_insert_dialog import (
    build_opex_assisted_base_dimensions,
    build_opex_assisted_inference_values,
    format_opex_assisted_inference,
)


pytestmark = pytest.mark.unit


def values(
    **overrides,
):
    result = {
        "presupuestador":
            "ANA TEST",
        "origen":
            "Local",
        "nombre_gasto":
            "LICENCIAS",
        "proveedor":
            "",
        "ceco":
            "001234",
    }

    result.update(
        overrides
    )

    return result


def test_base_dimensions_keep_user_values():
    result = (
        build_opex_assisted_base_dimensions(
            values()
        )
    )

    assert (
        result["presupuestador"]
        == "ANA TEST"
    )

    assert (
        result["origen"]
        == "Local"
    )

    assert (
        result["ceco"]
        == "001234"
    )


def test_inference_excludes_user_owned_dimensions():
    result = (
        build_opex_assisted_inference_values(
            values()
        )
    )

    assert (
        "presupuestador"
        not in result
    )

    assert "origen" not in result

    assert result == {
        "nombre_gasto":
            "LICENCIAS",
        "ceco":
            "001234",
    }


def test_required_user_dimensions_are_validated():
    with pytest.raises(
        ValueError,
        match="Presupuestador",
    ):
        (
            build_opex_assisted_base_dimensions(
                values(
                    presupuestador="   ",
                )
            )
        )


def test_at_least_one_historical_clue_is_required():
    with pytest.raises(
        ValueError,
        match="al menos un dato",
    ):
        (
            build_opex_assisted_base_dimensions(
                values(
                    nombre_gasto="",
                    proveedor="",
                    ceco="",
                )
            )
        )


def test_summary_hides_user_owned_historical_values():
    result = SimpleNamespace(
        matching_row_count=3,
        inferred_values=(
            (
                "pais",
                "Perú",
            ),
            (
                "presupuestador",
                "HISTORICO",
            ),
        ),
        ambiguous_values=(
            (
                "categoria_gasto",
                (
                    "SOFTWARE",
                    "LICENCIAS",
                ),
            ),
            (
                "origen",
                (
                    "Local",
                    "Regional",
                ),
            ),
        ),
        no_data_columns=(
            "segmentacion",
            "presupuestador",
        ),
    )

    text = (
        format_opex_assisted_inference(
            result
        )
    )

    assert (
        "Coincidencias historicas: 3"
        in text
    )

    assert "Pais: Perú" in text

    assert (
        "Categoria Gasto"
        in text
    )

    assert "Segmentacion" in text
    assert "HISTORICO" not in text
    assert "Regional" not in text
