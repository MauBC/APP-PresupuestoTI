
import pytest

from app.ui.dialogs.new_budget_row_dialog import (
    format_dimension_label,
    parse_dimension_value,
)


pytestmark = pytest.mark.unit


def test_formats_special_dimension_labels():
    assert (
        format_dimension_label(
            "codigo_ceco"
        )
        == "Codigo CECO"
    )

    assert (
        format_dimension_label(
            "moneda_facturacion"
        )
        == "Moneda de facturacion"
    )


def test_formats_generic_dimension_label():
    assert (
        format_dimension_label(
            "nombre_inversion"
        )
        == "Nombre Inversion"
    )


def test_parse_string_trims_value():
    assert (
        parse_dimension_value(
            "  PER  ",
            "STRING",
        )
        == "PER"
    )


def test_parse_blank_returns_none():
    assert (
        parse_dimension_value(
            "   ",
            "STRING",
        )
        is None
    )


def test_parse_integer():
    assert (
        parse_dimension_value(
            "2027",
            "INTEGER",
        )
        == 2027
    )


def test_invalid_integer_is_rejected():
    with pytest.raises(
        ValueError,
        match="entero",
    ):
        parse_dimension_value(
            "20.27",
            "INTEGER",
        )
