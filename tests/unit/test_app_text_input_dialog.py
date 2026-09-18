import pytest

from PySide6.QtWidgets import (
    QDialog,
)

import app.ui.dialogs.app_message_box as message_module


pytestmark = pytest.mark.unit


def test_ask_text_input_returns_custom_dialog_value(
    monkeypatch,
):
    captured = {}

    class FakeDialog:
        def __init__(
            self,
            **kwargs,
        ):
            captured.update(
                kwargs
            )

        def exec(
            self,
        ):
            return (
                QDialog.DialogCode
                .Accepted
            )

        def value(
            self,
        ):
            return "300.00"

    monkeypatch.setattr(
        message_module,
        "AppTextInputDialog",
        FakeDialog,
    )

    value, accepted = (
        message_module
        .ask_text_input(
            None,
            "Corregir",
            "Detalle",
            initial_value="300.00",
            expected_value="300.00",
            confirm_text=(
                "Aplicar correccion"
            ),
        )
    )

    assert accepted

    assert (
        value
        == "300.00"
    )

    assert (
        captured[
            "expected_value"
        ]
        == "300.00"
    )

    assert (
        captured[
            "initial_value"
        ]
        == "300.00"
    )

    assert (
        captured[
            "confirm_text"
        ]
        == "Aplicar correccion"
    )
